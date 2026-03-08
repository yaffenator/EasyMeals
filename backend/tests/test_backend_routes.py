import os
from datetime import datetime, timezone
from importlib import import_module
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

os.environ["TESTING"] = "true"


def _load_app_module():
    return import_module("backend")


def test_generate_plan_invalid_payload_returns_400():
    module = _load_app_module()
    client = TestClient(module.app)

    response = client.post(
        "/api/generate-plan",
        json={
            "userId": "user_1",
            "monthlyBudget": 20,
            "weight": 160.0,
            "goalType": "maintain",
            "dietaryTags": [],
            "allergies": [],
        },
    )

    assert response.status_code == 400


def test_generate_plan_active_lock_returns_409():
    module = _load_app_module()
    client = TestClient(module.app)

    payload = {
        "userId": "user_1",
        "monthlyBudget": 300,
        "weight": 160.0,
        "goalType": "maintain",
        "dietaryTags": [],
        "allergies": [],
    }
    with patch(
        "backend.generate_and_store_plan",
        side_effect=module.GenerationConflictError("Generation already in progress for user."),
    ):
        response = client.post("/api/generate-plan", json=payload)

    assert response.status_code == 409


def test_generate_plan_success_returns_hardening_fields():
    module = _load_app_module()
    client = TestClient(module.app)

    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "userId": "user_1",
        "planId": "plan_123",
        "status": "stored",
        "monthlyBudget": 300,
        "estimatedTotalCost": 120.0,
        "weeks": [],
        "groceryList": [],
        "metadata": {"planMonth": "2026-03", "planVersion": 2, "requestId": "req_123"},
    }
    payload = {
        "userId": "user_1",
        "monthlyBudget": 300,
        "weight": 170.0,
        "goalType": "maintain",
        "dietaryTags": [],
        "allergies": [],
    }
    with patch("backend.generate_and_store_plan", return_value=mock_response):
        response = client.post("/api/generate-plan", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "stored"
    assert body["metadata"]["planMonth"] == "2026-03"
    assert body["metadata"]["planVersion"] == 2


def test_get_plan_prefers_latest_active_plan():
    module = _load_app_module()
    client = TestClient(module.app)

    ready_old = MagicMock()
    ready_old.id = "plan_ready_old"
    ready_old.to_dict.return_value = {
        "status": "ready",
        "version": 1,
        "createdAt": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }

    generating_newer = MagicMock()
    generating_newer.id = "plan_generating"
    generating_newer.to_dict.return_value = {
        "status": "generating",
        "version": 5,
        "createdAt": datetime(2026, 3, 5, tzinfo=timezone.utc),
    }

    ready_new = MagicMock()
    ready_new.id = "plan_ready_new"
    ready_new.to_dict.return_value = {
        "status": "ready",
        "version": 2,
        "createdAt": datetime(2026, 3, 3, tzinfo=timezone.utc),
    }

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = [
        ready_old,
        generating_newer,
        ready_new,
    ]

    with patch("backend.db", mock_db):
        response = client.get("/api/get-plan/user_1")

    assert response.status_code == 200
    assert response.json()["planId"] == "plan_generating"
