#!/usr/bin/env python3
"""
Generate missing meal images for Firestore user plan docs.

Behavior:
- Scans users/{uid}/plans/*
- Generates image only if `image` is missing/empty/placeholder
- Retries failed items automatically across multiple passes
- Tracks generation fields on each meal doc:
  - imageGenStatus: pending|success|failed
  - imageGenAttempts: total model attempts so far
  - imageGenError: last error string (if failed)
- Uses the most basic image-capable model from your list by default:
  models/gemini-2.5-flash-image
- Uploads images to Firebase Storage (meal-images/<file>.png)
- Writes Firebase download URL back to Firestore

Env:
- GEMINI_API_KEY is required
- GOOGLE_APPLICATION_CREDENTIALS or backend/serviceAccountKey.json
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import quote

import firebase_admin
from firebase_admin import credentials, firestore, storage

try:
    from google import genai
    from google.genai import types
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency: google-genai. Install with `pip install google-genai`."
    ) from exc

DEFAULT_IMAGE_MODEL = "models/gemini-2.5-flash-image"
PLACEHOLDER_PREFIXES = ("/api/placeholder", "https://via.placeholder.com")


def resolve_storage_bucket(project_id: Optional[str]) -> str:
    configured = (
        os.environ.get("FIREBASE_STORAGE_BUCKET")
        or os.environ.get("NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET")
        or os.environ.get("NEXT_PUBLIC_storageBucket")
        or ""
    ).strip()
    if configured:
        return configured

    inferred_project = (
        project_id
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or ""
    ).strip()
    if inferred_project:
        return f"{inferred_project}.appspot.com"

    raise ValueError(
        "Could not resolve Firebase Storage bucket. Set FIREBASE_STORAGE_BUCKET "
        "or NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET."
    )


def init_firestore(project_id: Optional[str] = None) -> firestore.Client:
    if firebase_admin._apps:
        return firestore.client()

    key_path_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    script_dir = Path(__file__).resolve().parent
    local_key_path = script_dir / "serviceAccountKey.json"
    secrets_key_path = script_dir / "secrets" / "serviceAccountKey.json"

    if key_path_env:
        key_path = Path(key_path_env)
        if not key_path.exists():
            raise FileNotFoundError(
                f"GOOGLE_APPLICATION_CREDENTIALS is set, but file not found: {key_path}"
            )
        cred_obj = credentials.Certificate(str(key_path))
    elif local_key_path.exists():
        cred_obj = credentials.Certificate(str(local_key_path))
    elif secrets_key_path.exists():
        cred_obj = credentials.Certificate(str(secrets_key_path))
    else:
        raise FileNotFoundError(
            "No service account key found. Set GOOGLE_APPLICATION_CREDENTIALS or place "
            "serviceAccountKey.json in backend/ or backend/secrets/."
        )

    options = {"storageBucket": resolve_storage_bucket(project_id)}
    if project_id:
        options["projectId"] = project_id
    firebase_admin.initialize_app(cred_obj, options=options)
    return firestore.client()


def slugify(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "meal"


def needs_image(image_value: object) -> bool:
    if image_value is None:
        return True
    if not isinstance(image_value, str):
        return True

    v = image_value.strip()
    if not v:
        return True

    return any(v.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


def build_prompt(meal_name: str) -> str:
    return (
        "Create a realistic, appetizing, professional food photo of this meal: "
        f"{meal_name}. "
        "Top-down plating, natural lighting, no text, no watermark, clean background."
    )


def extract_image_bytes(response: object) -> bytes:
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                return inline_data.data
    raise ValueError("Model response did not include image bytes")


def generate_image_bytes(client: genai.Client, model: str, meal_name: str) -> bytes:
    prompt = build_prompt(meal_name)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            temperature=0.8,
        ),
    )
    return extract_image_bytes(response)


def upload_image_to_storage(bucket, blob_path: str, image_bytes: bytes) -> str:
    token = str(uuid.uuid4())
    blob = bucket.blob(blob_path)
    blob.metadata = {"firebaseStorageDownloadTokens": token}
    blob.cache_control = "public, max-age=31536000, immutable"
    blob.upload_from_string(image_bytes, content_type="image/png")
    blob.patch()
    encoded_blob_path = quote(blob_path, safe="")
    return (
        f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
        f"{encoded_blob_path}?alt=media&token={token}"
    )


def iter_user_refs(db: firestore.Client, user_id: Optional[str]) -> Iterable:
    if user_id:
        yield db.collection("users").document(user_id)
        return

    for user_doc in db.collection("users").stream():
        yield user_doc.reference


def should_process_meal(
    meal_data: dict,
    retry_failed: bool,
    max_attempts: int,
) -> bool:
    if not needs_image(meal_data.get("image")):
        return False

    attempts = int(meal_data.get("imageGenAttempts") or 0)
    status = str(meal_data.get("imageGenStatus") or "pending").lower()

    if attempts >= max_attempts:
        return False

    if status == "failed" and not retry_failed:
        return False

    return True


def try_generate_for_plan_meal(
    db: firestore.Client,
    bucket,
    client: genai.Client,
    model: str,
    plan_ref,
    weeks: list[dict],
    week_index: int,
    meal_index: int,
    meal: dict,
    uid: str,
    attempts_per_meal: int,
    max_attempts: int,
    dry_run: bool,
) -> Tuple[bool, int]:
    """Returns (success, attempts_used)."""
    meal_name = str(meal.get("name") or "Meal")
    current_attempts = int(meal.get("imageGenAttempts") or 0)
    meal_id = str(meal.get("id") or f"week{week_index}_meal{meal_index}")

    attempts_allowed = max(0, min(attempts_per_meal, max_attempts - current_attempts))
    if attempts_allowed <= 0:
        return False, 0

    slug = slugify(meal_name)
    filename = f"{uid}_{plan_ref.id}_{slugify(meal_id)}_{slug}.png"
    blob_path = f"meal-images/{filename}"
    storage_url = f"gs://{bucket.name}/{blob_path}"

    if dry_run:
        print(
            f"[DRY RUN] Would generate image for users/{uid}/plans/{plan_ref.id} "
            f"(week={week_index}, meal={meal_index}) -> {storage_url}"
        )
        return True, 1

    last_error = ""
    for attempt_index in range(1, attempts_allowed + 1):
        total_attempt_num = current_attempts + attempt_index
        try:
            weeks[week_index]["meals"][meal_index]["imageGenStatus"] = "pending"
            weeks[week_index]["meals"][meal_index]["imageGenAttempts"] = total_attempt_num
            plan_ref.update({"weeks": weeks, "updatedAt": firestore.SERVER_TIMESTAMP})

            image_bytes = generate_image_bytes(client, model, meal_name)
            image_url = upload_image_to_storage(bucket, blob_path, image_bytes)

            weeks[week_index]["meals"][meal_index]["image"] = image_url
            weeks[week_index]["meals"][meal_index]["imageGenStatus"] = "success"
            weeks[week_index]["meals"][meal_index].pop("imageGenError", None)
            plan_ref.update({"weeks": weeks, "updatedAt": firestore.SERVER_TIMESTAMP})

            if meal.get("id"):
                db.collection("recipes").document(meal_id).set(
                    {"image": image_url, "updatedAt": firestore.SERVER_TIMESTAMP},
                    merge=True,
                )

            print(
                f"Generated image for users/{uid}/plans/{plan_ref.id} "
                f"(week={week_index}, meal={meal_index}): {storage_url}"
            )
            return True, attempt_index
        except Exception as exc:
            last_error = str(exc)
            print(
                f"Attempt {total_attempt_num} failed for users/{uid}/plans/{plan_ref.id} "
                f"(week={week_index}, meal={meal_index}, name={meal_name}): {last_error}",
                file=sys.stderr,
            )
            time.sleep(1.5)

    weeks[week_index]["meals"][meal_index]["imageGenStatus"] = "failed"
    weeks[week_index]["meals"][meal_index]["imageGenError"] = last_error[:500]
    plan_ref.update({"weeks": weeks, "updatedAt": firestore.SERVER_TIMESTAMP})
    return False, attempts_allowed


def run(
    db: firestore.Client,
    bucket,
    client: genai.Client,
    model: str,
    user_id: Optional[str],
    limit: Optional[int],
    dry_run: bool,
    retry_failed: bool,
    max_attempts: int,
    attempts_per_meal: int,
    passes: int,
) -> int:
    generated_total = 0
    checked_total = 0

    for pass_num in range(1, passes + 1):
        pass_generated = 0
        pass_checked = 0
        pass_attempted = 0

        for user_ref in iter_user_refs(db, user_id):
            uid = user_ref.id
            plan_docs = list(user_ref.collection("plans").stream())

            for plan_doc in plan_docs:
                plan_data = plan_doc.to_dict() or {}
                weeks = plan_data.get("weeks") or []

                for week_index, week in enumerate(weeks):
                    meals = week.get("meals") or []
                    for meal_index, meal_data in enumerate(meals):
                        pass_checked += 1
                        checked_total += 1

                        if not should_process_meal(
                            meal_data=meal_data,
                            retry_failed=retry_failed,
                            max_attempts=max_attempts,
                        ):
                            continue

                        if limit is not None and generated_total >= limit:
                            print(f"Reached limit={limit}; stopping.")
                            print(f"Checked {checked_total} meals, generated {generated_total} images.")
                            return 0

                        pass_attempted += 1
                        success, _attempts_used = try_generate_for_plan_meal(
                            db=db,
                            bucket=bucket,
                            client=client,
                            model=model,
                            plan_ref=plan_doc.reference,
                            weeks=weeks,
                            week_index=week_index,
                            meal_index=meal_index,
                            meal=meal_data,
                            uid=uid,
                            attempts_per_meal=attempts_per_meal,
                            max_attempts=max_attempts,
                            dry_run=dry_run,
                        )

                        if success:
                            generated_total += 1
                            pass_generated += 1

        print(
            f"Pass {pass_num}/{passes}: checked {pass_checked} meals, attempted {pass_attempted}, generated {pass_generated} images."
        )

        if pass_attempted == 0:
            break

    print(f"Done. Checked {checked_total} meals, generated {generated_total} images.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate missing meal images and update Firestore.")
    parser.add_argument("--project", dest="project_id", default=None, help="Override Firebase project id.")
    parser.add_argument("--user-id", dest="user_id", default=None, help="Only process one user UID.")
    parser.add_argument("--model", dest="model", default=DEFAULT_IMAGE_MODEL, help="Image model id.")
    parser.add_argument("--limit", dest="limit", type=int, default=None, help="Max images to generate.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Print actions without writing.")
    parser.add_argument("--max-attempts", dest="max_attempts", type=int, default=8, help="Max total attempts per meal doc.")
    parser.add_argument("--attempts-per-meal", dest="attempts_per_meal", type=int, default=2, help="Attempts per meal in each pass.")
    parser.add_argument("--passes", dest="passes", type=int, default=3, help="How many full rerun passes to execute.")
    parser.add_argument("--retry-failed", dest="retry_failed", action="store_true", default=True, help="Include previously failed meals in reruns.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY is required.", file=sys.stderr)
        return 1

    try:
        db = init_firestore(project_id=args.project_id)
        bucket = storage.bucket(resolve_storage_bucket(args.project_id))
        client = genai.Client(api_key=api_key)

        return run(
            db=db,
            bucket=bucket,
            client=client,
            model=args.model,
            user_id=args.user_id,
            limit=args.limit,
            dry_run=args.dry_run,
            retry_failed=args.retry_failed,
            max_attempts=args.max_attempts,
            attempts_per_meal=args.attempts_per_meal,
            passes=args.passes,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
