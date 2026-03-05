from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()

from db.firestore_client import db
from db.plan_service import GenerationConflictError, PlanGenerationRequest, generate_and_store_plan
from db.rating_service import rate_meal

app = FastAPI(title="EasyMeals Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateMealRequest(BaseModel):
    mealId: str
    userId: str
    rating: int


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
def generate_plan(payload: dict[str, Any]):
    try:
        request = PlanGenerationRequest(**payload)
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
def rate_meal_endpoint(payload: RateMealRequest):
    try:
        updated = rate_meal(payload.mealId, payload.userId, payload.rating)
        return {"ok": True, "mealId": payload.mealId, "updated": _serialize_firestore(updated)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to rate meal: {exc}") from exc


@app.get("/api/get-plan/{user_id}")
def get_plan(user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore client is not initialized.")

    try:
        plan_docs = list(db.collection("users").document(user_id).collection("plans").stream())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plans: {exc}") from exc

    if not plan_docs:
        raise HTTPException(status_code=404, detail=f"No plans found for user {user_id}.")

    ready_docs = [doc for doc in plan_docs if (doc.to_dict() or {}).get("status") == "ready"]
    candidate_docs = ready_docs if ready_docs else plan_docs
    candidate_docs.sort(key=_plan_sort_key, reverse=True)
    latest_doc = candidate_docs[0]
    latest_data = latest_doc.to_dict() or {}

    return {
        "userId": user_id,
        "planId": latest_doc.id,
        "plan": _serialize_firestore(latest_data),
    }
