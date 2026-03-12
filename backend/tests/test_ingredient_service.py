import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# Unit Tests - pure functions, no Firestore needed
# ============================================================

def test_normalize_name_strips_and_lowercases():
    with patch("db.firestore_client.db", MagicMock()):
        from db.ingredient_service import normalize_name
        assert normalize_name("  Chicken Breast  ") == "chicken breast"
        assert normalize_name("RICE") == "rice"
        assert normalize_name("salmon") == "salmon"

def test_normalize_unit_maps_correctly():
    with patch("db.firestore_client.db", MagicMock()):
        from db.ingredient_service import normalize_unit
        assert normalize_unit("Grams") == "g"
        assert normalize_unit("pounds") == "lb"
        assert normalize_unit("TBSP") == "tbsp"
        assert normalize_unit("cups") == "cup"

def test_normalize_unit_passthrough_unknown():
    with patch("db.firestore_client.db", MagicMock()):
        from db.ingredient_service import normalize_unit
        assert normalize_unit("unknown_unit") == "unknown_unit"


# ============================================================
# Validation Tests - component behavior with mocked Firestore
# ============================================================

def test_get_or_create_returns_existing_ingredient():
    mock_doc = MagicMock()
    mock_doc.id = "ingredient_chicken_breast_meat"

    mock_db = MagicMock()
    mock_db.collection().where().stream.return_value = [mock_doc]

    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.ingredient_service.db", mock_db):
            from db.ingredient_service import get_or_create_ingredient
            result = get_or_create_ingredient("chicken breast", "g", 3.49, "lb", "meat")
            assert result == "ingredient_chicken_breast_meat"
            mock_db.collection().document().set.assert_not_called()

def test_get_or_create_creates_new_ingredient():
    mock_db = MagicMock()
    mock_db.collection().where().stream.return_value = []

    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.ingredient_service.db", mock_db):
            from db.ingredient_service import get_or_create_ingredient
            result = get_or_create_ingredient("salmon", "g", 7.99, "lb", "fish")
            assert result == "ingredient_salmon_fish"
            mock_db.collection().document().set.assert_called_once()

def test_recalculate_meal_cost_raises_on_missing_ingredient():
    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.ingredient_service.MASTER_PRICES", {}):
            from db.ingredient_service import recalculate_meal_cost
            cost = recalculate_meal_cost([{"ingredientId": "fake_id", "quantity": 100, "unit": "g"}])
            assert cost == 0.0

def test_recalculate_meal_cost_same_units():
    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.ingredient_service.MASTER_PRICES", {"some_id": {"price": 2.0, "unit": "g", "name": "some"}}):
            from db.ingredient_service import recalculate_meal_cost
            cost = recalculate_meal_cost([{"ingredientId": "some_id", "quantity": 3, "unit": "g"}])
            assert cost == 6.0

def test_recalculate_meal_cost_resolves_firestore_style_id():
    with patch("db.firestore_client.db", MagicMock()):
        with patch("db.ingredient_service.MASTER_PRICES", {"chicken_breast": {"price": 2.0, "unit": "lb", "name": "chicken breast"}}):
            from db.ingredient_service import recalculate_meal_cost
            cost = recalculate_meal_cost([{"ingredientId": "ingredient_chicken_breast_meat", "quantity": 2, "unit": "lb"}])
            assert cost == 4.0

def test_recalculate_meal_cost_clamps_extreme_values():
    with patch("db.firestore_client.db", MagicMock()):
        # Price is intentionally extreme and should be clamped.
        with patch("db.ingredient_service.MASTER_PRICES", {"some_id": {"price": 9999.0, "unit": "cup", "name": "some"}}):
            from db.ingredient_service import recalculate_meal_cost
            # Quantity is intentionally extreme and should be clamped to 8 cups.
            cost = recalculate_meal_cost([{"ingredientId": "some_id", "quantity": 1000, "unit": "cup"}])
            assert cost == 200.0
