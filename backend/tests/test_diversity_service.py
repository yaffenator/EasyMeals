import pytest
import math
from unittest.mock import MagicMock, patch


# ============================================================
# Unit Tests - pure functions
# ============================================================

def test_compute_diversity_weight_no_recent_meals():
    with patch("db.firestore_client.db", MagicMock()):
        from db.diversity_service import compute_diversity_weight
        # n=0 means never eaten recently, should be e^0 = 1.0
        assert compute_diversity_weight(0) == 1.0

def test_compute_diversity_weight_decays_with_repetition():
    with patch("db.firestore_client.db", MagicMock()):
        from db.diversity_service import compute_diversity_weight
        weight_0 = compute_diversity_weight(0)
        weight_1 = compute_diversity_weight(1)
        weight_2 = compute_diversity_weight(2)
        assert weight_0 > weight_1 > weight_2

def test_compute_diversity_weight_never_zero():
    with patch("db.firestore_client.db", MagicMock()):
        from db.diversity_service import compute_diversity_weight
        # Should never reach 0, meals are penalized not banned
        assert compute_diversity_weight(100) > 0


# ============================================================
# Validation Tests
# ============================================================

def test_compute_final_scores_attaches_scores():
    mock_db = MagicMock()
    mock_db.collection().document().collection().where().stream.return_value = []

    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.diversity_service.db", mock_db):
            from db.diversity_service import compute_final_scores
            candidates = [
                {"mealId": "meal_1", "recommendationScore": 4.0},
                {"mealId": "meal_2", "recommendationScore": 3.0},
            ]
            result = compute_final_scores("user_123", candidates)
            assert all("finalScore" in meal for meal in result)
            assert all("diversityWeight" in meal for meal in result)

def test_compute_final_scores_penalizes_recent_meals():
    mock_history_doc = MagicMock()
    mock_history_doc.to_dict.return_value = {"mealId": "meal_1"}

    mock_db = MagicMock()
    # match the exact chain: .collection().document().collection().where().stream()
    mock_db.collection.return_value.document.return_value.collection.return_value.where.return_value.stream.return_value = [
        mock_history_doc, mock_history_doc  # meal_1 eaten twice
    ]

    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.diversity_service.db", mock_db):
            from db.diversity_service import compute_final_scores
            candidates = [
                {"mealId": "meal_1", "recommendationScore": 4.0},
                {"mealId": "meal_2", "recommendationScore": 4.0},
            ]
            result = compute_final_scores("user_123", candidates)
            meal_1 = next(m for m in result if m["mealId"] == "meal_1")
            meal_2 = next(m for m in result if m["mealId"] == "meal_2")
            assert meal_1["finalScore"] < meal_2["finalScore"]

def test_sample_meals_returns_correct_count():
    with patch("db.firestore_client.db", MagicMock()):
        from db.diversity_service import sample_meals
        meals = [{"mealId": f"meal_{i}", "finalScore": 1.0} for i in range(10)]
        result = sample_meals(meals, 5)
        assert len(result) == 5

def test_sample_meals_empty_input():
    with patch("db.firestore_client.db", MagicMock()):
        from db.diversity_service import sample_meals
        assert sample_meals([], 5) == []