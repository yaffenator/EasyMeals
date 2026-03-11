import json
import os

import firebase_admin
from firebase_admin import credentials, firestore


def _load_env_credentials():
    raw_creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if not raw_creds:
        return None

    try:
        return credentials.Certificate(json.loads(raw_creds))
    except json.JSONDecodeError as exc:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT is set, but it is not valid JSON.") from exc


def _init_db():
    if firebase_admin._apps:
        return firestore.client()

    cred_obj = _load_env_credentials()
    if cred_obj is None:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cred_path = os.path.join(BASE_DIR, "secrets", "serviceAccountKey.json")
        if not os.path.exists(cred_path):
            return None  # Let tests mock this, don't crash
        cred_obj = credentials.Certificate(cred_path)

    firebase_admin.initialize_app(cred_obj)
    return firestore.client()

db = _init_db()
