from unittest.mock import MagicMock, patch

import pytest


def _valid_gemini_payload():
    return {
        "mealPlan": [
            {
                "name": "Egg Scramble",
                "calories": 350,
                "carbs": 10,
                "fat": 20,
                "protein": 25,
                "prepTime": "5 minutes",
                "cookTime": "10 minutes",
                "servings": 1,
                "costPerServing": 2.5,
                "mealType": "Breakfast",
                "difficulty": "Easy",
                "instructions": "Cook eggs in a pan.",
                "tags": ["high-protein"],
                "ingredientItems": [
                    {
                        "ingredientId": "ingredient_eggs_protein",
                        "originalText": "2 eggs",
                        "quantity": 2,
                        "unit": "piece",
                        "notes": "",
                    }
                ],
                "ingredients": ["Eggs"],
            }
        ],
        "ingredientPrices": {
            "ingredient_eggs_protein": {
                "name": "eggs",
                "category": "protein",
                "defaultUnit": "piece",
                "price": {
                    "value": 0.4,
                    "currency": "USD",
                    "unitQuantity": 1,
                    "unit": "piece",
                },
            }
        },
    }


def test_generate_and_store_plan_calls_gemini_and_returns_step_2_stub():
    with patch("db.firestore_client.db", MagicMock()):
        from db.gemini_service import GeminiResponse
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=300.0,
            goalType="maintain",
            dietaryTags=["high-protein"],
            allergies=["peanut"],
        )

        with patch("db.plan_service.db", MagicMock()):
            with patch(
                "db.plan_service.generate_meal_plan",
                return_value=GeminiResponse(**_valid_gemini_payload()),
            ) as mock_generate:
                result = generate_and_store_plan(request)

        assert result.status == "gemini_validated"
        assert result.metadata["implementedStep"] == 2
        assert result.metadata["mealCount"] == 1
        assert result.metadata["ingredientPriceCount"] == 1
        mock_generate.assert_called_once()


def test_generate_and_store_plan_raises_if_db_not_initialized():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=200.0,
            goalType="lose",
        )

        with patch("db.plan_service.db", None):
            with pytest.raises(ValueError, match="Firestore client is not initialized"):
                generate_and_store_plan(request)


def test_generate_and_store_plan_wraps_gemini_errors():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=400.0,
            goalType="gain",
        )

        with patch("db.plan_service.db", MagicMock()):
            with patch("db.plan_service.generate_meal_plan", side_effect=ValueError("malformed response")):
                with pytest.raises(ValueError, match="Failed to generate validated Gemini meal plan"):
                    generate_and_store_plan(request)
