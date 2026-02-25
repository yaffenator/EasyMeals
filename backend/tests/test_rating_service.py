import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# Unit Tests - pure functions
# ============================================================

def test_compute_bayesian_score_high_vote_count():
    with patch("db.firestore_client.db", MagicMock()):
        from db.rating_service import compute_bayesian_score
        # With lots of ratings, score should be close to meal's own average
        score = compute_bayesian_score(R=4.8, v=1000, m=3.0, C=10)
        assert score > 4.5

def test_compute_bayesian_score_low_vote_count():
    with patch("db.firestore_client.db", MagicMock()):
        from db.rating_service import compute_bayesian_score
        # With very few ratings, score should be pulled toward global average
        score = compute_bayesian_score(R=5.0, v=1, m=3.0, C=10)
        assert score < 4.0

def test_compute_bayesian_score_formula():
    with patch("db.firestore_client.db", MagicMock()):
        from db.rating_service import compute_bayesian_score
        # ((2 * 4.0) + (3.0 * 10)) / (2 + 10) = 38 / 12 = 3.166...
        score = compute_bayesian_score(R=4.0, v=2, m=3.0, C=10)
        assert round(score, 3) == 3.167


# ============================================================
# Validation Tests
# ============================================================

def test_rate_meal_invalid_rating_too_low():
    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.rating_service.db", MagicMock()):
            from db.rating_service import rate_meal
            with pytest.raises(ValueError):
                rate_meal("some_meal_id", "some_user_id", 0)

def test_rate_meal_invalid_rating_too_high():
    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.rating_service.db", MagicMock()):
            from db.rating_service import rate_meal
            with pytest.raises(ValueError):
                rate_meal("some_meal_id", "some_user_id", 6)

def test_rate_meal_missing_meal():
    mock_meal_doc = MagicMock()
    mock_meal_doc.exists = False

    mock_db = MagicMock()
    mock_db.collection().document().get.return_value = mock_meal_doc

    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.rating_service.db", mock_db):
            from db.rating_service import rate_meal
            with pytest.raises(ValueError):
                rate_meal("nonexistent_meal", "some_user_id", 4)

def test_rate_meal_returns_updated_stats():
    mock_meal_doc = MagicMock()
    mock_meal_doc.exists = True
    mock_meal_doc.to_dict.return_value = {
        "ratingCount": 10,
        "ratingSum": 40.0,
        "ratingAvg": 4.0,
    }

    mock_stats_doc = MagicMock()
    mock_stats_doc.to_dict.return_value = {
        "totalRatingSum": 40.0,
        "totalRatingCount": 10,
        "globalAvg": 3.5,
    }

    mock_meals_ref = MagicMock()
    mock_meals_ref.document.return_value.get.return_value = mock_meal_doc

    mock_meta_ref = MagicMock()
    mock_meta_ref.document.return_value.get.return_value = mock_stats_doc

    mock_db = MagicMock()
    mock_db.collection.side_effect = lambda name: {
        "meals": mock_meals_ref,
        "meta": mock_meta_ref,
    }[name]

    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.rating_service.db", mock_db):
            from db.rating_service import rate_meal
            result = rate_meal("some_meal_id", "some_user_id", 5)
            assert result["ratingCount"] == 11
            assert result["ratingAvg"] == round(45.0 / 11, 4)