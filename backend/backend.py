from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

load_dotenv()

if not firebase_admin._apps:
    firebase_env_creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()

    if firebase_env_creds:
        try:
            cred = credentials.Certificate(json.loads(firebase_env_creds))
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT is set, but it is not valid JSON.") from exc
    else:
        # Local fallback for development.
        local_cred_path = Path(__file__).resolve().parent / "secrets" / "serviceAccountKey.json"
        cred = credentials.Certificate(str(local_cred_path))

    firebase_admin.initialize_app(cred)

# Now that Firebase is initialized, these files can safely call firestore.client()
from db.firestore_client import db
from db.plan_service import GenerationConflictError, PlanGenerationRequest, generate_and_store_plan
from db.rating_service import rate_meal

app = FastAPI(title="EasyMeals Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateMealRequest(BaseModel):
    mealId: str
    userId: str
    rating: int


def _is_testing_mode() -> bool:
    return os.environ.get("TESTING", "").lower() == "true"


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Authorization must use Bearer token.")
    token = authorization[len(prefix) :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token is empty.")
    return token


def _authorize_user(user_id: str, authorization: str | None) -> None:
    if _is_testing_mode():
        return

    token = _extract_bearer_token(authorization)
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase ID token: {exc}") from exc

    token_uid = decoded.get("uid")
    if token_uid != user_id:
        raise HTTPException(status_code=403, detail="Token user does not match requested user.")


def _serialize_firestore(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _serialize_firestore(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_firestore(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    # Firestore DocumentReference objects expose `path`.
    if hasattr(value, "path"):
        try:
            return value.path
        except Exception:
            return str(value)
    return value


def _created_at_sort_key(doc: Any) -> float:
    created_at = (doc.to_dict() or {}).get("createdAt")
    if created_at is None:
        return 0.0
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at.timestamp()
    if hasattr(created_at, "timestamp"):
        try:
            return float(created_at.timestamp())
        except Exception:
            return 0.0
    return 0.0


def _plan_sort_key(doc: Any) -> tuple[float, int]:
    data = doc.to_dict() or {}
    created_at_ts = _created_at_sort_key(doc)
    version = data.get("version")
    if not isinstance(version, int):
        version = 0
    return (created_at_ts, version)


@app.get("/health")
def health_check():
    return {"ok": True, "service": "easymeals-backend"}


@app.post("/api/generate-plan")
def generate_plan(payload: dict[str, Any], authorization: str | None = Header(default=None)):
    try:
        request = PlanGenerationRequest(**payload)
        _authorize_user(request.userId, authorization)
        response = generate_and_store_plan(request)
        return _serialize_firestore(response.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GenerationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {exc}") from exc


@app.post("/api/rate-meal")
def rate_meal_endpoint(payload: RateMealRequest, authorization: str | None = Header(default=None)):
    try:
        _authorize_user(payload.userId, authorization)
        updated = rate_meal(payload.mealId, payload.userId, payload.rating)
        return {"ok": True, "mealId": payload.mealId, "updated": _serialize_firestore(updated)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to rate meal: {exc}") from exc


@app.get("/api/get-plan/{user_id}")
def get_plan(user_id: str, authorization: str | None = Header(default=None)):
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore client is not initialized.")
    _authorize_user(user_id, authorization)

    try:
        plan_docs = list(db.collection("users").document(user_id).collection("plans").stream())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plans: {exc}") from exc

    if not plan_docs:
        raise HTTPException(status_code=404, detail=f"No plans found for user {user_id}.")

    candidate_docs = [
        doc for doc in plan_docs if (doc.to_dict() or {}).get("status") in {"generating", "ready"}
    ]
    if not candidate_docs:
        candidate_docs = plan_docs
    candidate_docs.sort(key=_plan_sort_key, reverse=True)
    latest_doc = candidate_docs[0]
    latest_data = latest_doc.to_dict() or {}

    return {
        "userId": user_id,
        "planId": latest_doc.id,
        "plan": _serialize_firestore(latest_data),
    }
