#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore


DEFAULT_COLLECTIONS = ("users", "recipes", "ingredients", "meta")
SENTINEL_DOC_ID = "_keepalive"


def init_firestore(project_id: Optional[str] = None) -> firestore.Client:
    if firebase_admin._apps:
        return firestore.client()

    firebase_env_creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    backend_root = Path(__file__).resolve().parent.parent
    local_candidates = [
        backend_root / "secrets" / "serviceAccountKey.json",
        backend_root / "serviceAccountKey.json",
    ]

    if firebase_env_creds:
        try:
            cred_obj = credentials.Certificate(json.loads(firebase_env_creds))
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT is set, but it is not valid JSON.") from exc
    else:
        existing_local = next((p for p in local_candidates if p.exists()), None)
        if not existing_local:
            raise FileNotFoundError(
                "No service account key found. Set FIREBASE_SERVICE_ACCOUNT or place "
                "serviceAccountKey.json in backend/secrets/."
            )
        cred_obj = credentials.Certificate(str(existing_local))

    options = {"projectId": project_id} if project_id else None
    firebase_admin.initialize_app(cred_obj, options=options)
    return firestore.client()


def delete_collection(coll_ref, batch_size: int = 200) -> None:
    docs = list(coll_ref.limit(batch_size).stream())
    if not docs:
        return

    for doc in docs:
        for sub in doc.reference.collections():
            delete_collection(sub, batch_size=batch_size)
        doc.reference.delete()

    if len(docs) >= batch_size:
        delete_collection(coll_ref, batch_size=batch_size)


def delete_document_tree(doc_ref, batch_size: int = 200) -> None:
    for sub in doc_ref.collections():
        delete_collection(sub, batch_size=batch_size)
    doc_ref.delete()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete Firestore documents recursively.")
    parser.add_argument(
        "--collections",
        nargs="+",
        default=list(DEFAULT_COLLECTIONS),
        help="Top-level collections to clear.",
    )
    parser.add_argument("--project", dest="project_id", default=None, help="Override Firebase project id.")
    parser.add_argument(
        "--user-id",
        dest="user_ids",
        nargs="+",
        default=[],
        help="Delete specific users/{uid} trees recursively.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        db = init_firestore(project_id=args.project_id)
        for user_id in args.user_ids:
            delete_document_tree(db.collection("users").document(user_id))
            print(f"deleted users/{user_id}")
        for collection_name in args.collections:
            delete_collection(db.collection(collection_name))
            print(f"deleted {collection_name}")
            db.collection(collection_name).document(SENTINEL_DOC_ID).set(
                {"keepalive": True, "note": "Delete this doc if you want the collection hidden when empty."}
            )
            print(f"created {collection_name}/{SENTINEL_DOC_ID}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
