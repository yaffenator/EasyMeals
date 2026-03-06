from datetime import datetime, timezone
from importlib import import_module
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _load_app_module():
    return import_module("backend")


def test_health_route_returns_ok():
    module = _load_app_module()
    client = TestClient(module.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_generate_plan_route_success():
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
        "metadata": {},
    }

    payload = {
        "userId": "user_1",
        "monthlyBudget": 300,
        "goalType": "maintain",
        "dietaryTags": [],
        "allergies": [],
    }

    with patch("backend.generate_and_store_plan", return_value=mock_response):
        response = client.post("/api/generate-plan", json=payload)

    assert response.status_code == 200
    assert response.json()["planId"] == "plan_123"


def test_generate_plan_route_validation_error():
    module = _load_app_module()
    client = TestClient(module.app)

    payload = {
        "userId": "user_1",
        "monthlyBudget": -10,
        "goalType": "maintain",
        "dietaryTags": [],
        "allergies": [],
    }

    response = client.post("/api/generate-plan", json=payload)
    assert response.status_code == 422


def test_rate_meal_route_success():
    module = _load_app_module()
    client = TestClient(module.app)

    payload = {"mealId": "recipe_1", "userId": "user_1", "rating": 5}
    with patch(
        "backend.rate_meal",
        return_value={"ratingCount": 4, "ratingAvg": 4.75, "recommendationScore": 4.5},
    ):
        response = client.post("/api/rate-meal", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mealId"] == "recipe_1"
    assert body["updated"]["ratingCount"] == 4


def test_get_plan_route_returns_latest_plan():
    module = _load_app_module()
    client = TestClient(module.app)

    old_doc = MagicMock()
    old_doc.id = "plan_old"
    old_doc.to_dict.return_value = {"createdAt": datetime(2026, 1, 1, tzinfo=timezone.utc), "status": "ready"}

    new_doc = MagicMock()
    new_doc.id = "plan_new"
    new_doc.to_dict.return_value = {"createdAt": datetime(2026, 2, 1, tzinfo=timezone.utc), "status": "ready"}

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = [old_doc, new_doc]

    with patch("backend.db", mock_db):
        response = client.get("/api/get-plan/user_1")

    assert response.status_code == 200
    body = response.json()
    assert body["planId"] == "plan_new"
    assert body["userId"] == "user_1"


def test_get_plan_route_404_when_missing():
    module = _load_app_module()
    client = TestClient(module.app)

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = []

    with patch("backend.db", mock_db):
        response = client.get("/api/get-plan/user_1")

    assert response.status_code == 404
