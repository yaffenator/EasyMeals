from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db.firestore_client import db
from db.plan_service import PlanGenerationRequest, generate_and_store_plan
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


@app.post("/api/generate-plan")
def generate_plan(payload: PlanGenerationRequest):
    try:
        response = generate_and_store_plan(payload)
        return _serialize_firestore(response.model_dump())
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

    # Latest first by createdAt when available, fallback to first stream item.
    plan_docs.sort(
        key=lambda doc: (doc.to_dict() or {}).get("createdAt") or datetime.min,
        reverse=True,
    )
    latest_doc = plan_docs[0]
    latest_data = latest_doc.to_dict() or {}

    return {
        "userId": user_id,
        "planId": latest_doc.id,
        "plan": _serialize_firestore(latest_data),
    }
