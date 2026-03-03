# seed_users.py
#!/usr/bin/env python3
"""
Seeds Firestore users/{uid} docs to include the new health questionnaire fields
(from MealPlanWizard), and optionally creates an empty mealPlans subcollection doc.

User schema additions:
- monthlyBudget: number
- mealPlanProfile: {
    goal: "lose" | "gain" | "maintain",
    allergies: string[],
    excludedCuisines: string[],
    version: number,
    completedAt: timestamp
  }
- updatedAt: timestamp
- createdAt: timestamp

Run:
  python seed_users.py --user-id demo_user
Optional:
  python seed_users.py --project YOUR_PROJECT_ID
  python seed_users.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore


# -----------------------------
# Firebase init
# -----------------------------

def init_firestore(project_id: Optional[str] = None) -> firestore.Client:
    if firebase_admin._apps:
        return firestore.client()

    key_path_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    script_dir = Path(__file__).resolve().parent
    local_key_path = script_dir / "serviceAccountKey.json"

    if key_path_env:
        p = Path(key_path_env)
        if not p.exists():
            raise FileNotFoundError(f"GOOGLE_APPLICATION_CREDENTIALS is set, but file not found: {p}")
        cred_obj = credentials.Certificate(str(p))
    elif local_key_path.exists():
        cred_obj = credentials.Certificate(str(local_key_path))
    else:
        raise FileNotFoundError(
            "No service account key found. Set GOOGLE_APPLICATION_CREDENTIALS or place "
            "serviceAccountKey.json next to this script."
        )

    options: Dict[str, Any] = {}
    if project_id:
        options["projectId"] = project_id

    firebase_admin.initialize_app(cred_obj, options=options or None)
    return firestore.client()


def now_ts() -> datetime:
    return datetime.now(timezone.utc)


def build_user_doc(
    monthly_budget: float,
    goal: str,
    allergies: List[str],
    excluded_cuisines: List[str],
    version: int = 1,
) -> Dict[str, Any]:
    return {
        "monthlyBudget": monthly_budget,
        "mealPlanProfile": {
            "goal": goal,
            "allergies": allergies,
            "excludedCuisines": excluded_cuisines,
            "version": version,
            "completedAt": now_ts(),
        },
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": now_ts(),
    }


def seed_user(
    db: firestore.Client,
    user_id: str,
    monthly_budget: float,
    goal: str,
    allergies: List[str],
    excluded_cuisines: List[str],
    create_blank_mealplan: bool,
    dry_run: bool,
) -> None:
    user_ref = db.collection("users").document(user_id)
    doc = build_user_doc(monthly_budget, goal, allergies, excluded_cuisines)

    if dry_run:
        print(f"[DRY RUN] Would upsert users/{user_id} with questionnaire fields")
    else:
        user_ref.set(doc, merge=True)
        print(f"Upserted users/{user_id}")

    if create_blank_mealplan:
        meal_plan_id = uuid.uuid4().hex
        mp_ref = user_ref.collection("mealPlans").document(meal_plan_id)
        mp_doc = {
            "startDate": None,
            "endDate": None,
            "weeks": [],
            "createdAt": now_ts(),
            "updatedAt": now_ts(),
            "note": "Placeholder meal plan. Replace with generated plan.",
        }

        if dry_run:
            print(f"[DRY RUN] Would create users/{user_id}/mealPlans/{meal_plan_id} placeholder")
        else:
            mp_ref.set(mp_doc, merge=True)
            print(f"Created users/{user_id}/mealPlans/{meal_plan_id} placeholder")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed Firestore users with MealPlanWizard questionnaire fields.")
    p.add_argument("--project", dest="project_id", default=None)
    p.add_argument("--user-id", dest="user_id", required=True)
    p.add_argument("--monthly-budget", dest="monthly_budget", type=float, default=400.0)
    p.add_argument("--goal", dest="goal", choices=["lose", "gain", "maintain"], default="maintain")
    p.add_argument("--allergies", dest="allergies", default="", help="Comma-separated list (e.g., Milk,Peanuts)")
    p.add_argument("--excluded-cuisines", dest="excluded_cuisines", default="", help="Comma-separated list")
    p.add_argument("--create-blank-mealplan", dest="create_blank_mealplan", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    return p.parse_args()


def split_csv(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> int:
    args = parse_args()
    try:
        db = init_firestore(project_id=args.project_id)
        seed_user(
            db=db,
            user_id=args.user_id,
            monthly_budget=args.monthly_budget,
            goal=args.goal,
            allergies=split_csv(args.allergies),
            excluded_cuisines=split_csv(args.excluded_cuisines),
            create_blank_mealplan=args.create_blank_mealplan,
            dry_run=args.dry_run,
        )
        print("Done.")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
