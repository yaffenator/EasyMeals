import json
import time
from unittest.mock import patch

import pytest


def _valid_payload():
    return {
        "mealPlan": [
            {
                "name": "Oatmeal Bowl",
                "calories": 420,
                "carbs": 55,
                "fat": 10,
                "protein": 20,
                "prepTime": "5 minutes",
                "cookTime": "10 minutes",
                "servings": 1,
                "costPerServing": 2.25,
                "mealType": "Breakfast",
                "difficulty": "Easy",
                "instructions": "Mix oats and water and cook.",
                "tags": ["budget-friendly"],
                "ingredientItems": [
                    {
                        "ingredientId": "ingredient_oats_grains",
                        "originalText": "1 cup oats",
                        "quantity": 1,
                        "unit": "cup",
                        "notes": "",
                    }
                ],
                "ingredients": ["Rolled Oats"],
            }
        ],
        "ingredientPrices": {
            "ingredient_oats_grains": {
                "name": "rolled oats",
                "category": "grains",
                "defaultUnit": "cup",
                "price": {
                    "value": 0.30,
                    "currency": "USD",
                    "unitQuantity": 1,
                    "unit": "cup",
                },
            }
        },
    }


def test_extract_json_text_with_markdown_fence():
    from db.gemini_service import _extract_json_text

    payload = '{"mealPlan": [], "ingredientPrices": {}}'
    text = f"```json\n{payload}\n```"
    assert _extract_json_text(text) == payload


def test_call_gemini_returns_validated_response():
    with patch("db.gemini_service._generate_raw_response", return_value=json.dumps(_valid_payload())):
        from db.gemini_service import call_gemini

        result = call_gemini("prompt", retries=1)
        assert len(result.mealPlan) == 1
        assert "ingredient_oats_grains" in result.ingredientPrices


def test_call_gemini_retries_on_invalid_then_succeeds():
    responses = iter(["not json", json.dumps(_valid_payload())])

    with patch("db.gemini_service._generate_raw_response", side_effect=lambda _: next(responses)):
        from db.gemini_service import call_gemini

        result = call_gemini("prompt", retries=2)
        assert result.mealPlan[0].name == "Oatmeal Bowl"


def test_call_gemini_raises_after_retry_exhaustion():
    with patch("db.gemini_service._generate_raw_response", return_value="not json"):
        from db.gemini_service import call_gemini

        with pytest.raises(ValueError):
            call_gemini("prompt", retries=2)


def test_generate_meal_plan_builds_prompt_and_calls_service():
    with patch("db.gemini_service.call_gemini") as mock_call:
        from db.gemini_service import GeminiResponse, generate_meal_plan

        mock_call.return_value = GeminiResponse(**_valid_payload())
        preferences = {
            "monthlyBudget": 300,
            "goalType": "maintain",
            "dietaryTags": ["high-protein"],
            "allergies": ["peanut"],
        }
        result = generate_meal_plan(preferences, retries=2)

        assert result.mealPlan[0].mealType == "Breakfast"
        mock_call.assert_called_once()


def test_call_gemini_times_out_and_raises():
    with patch("db.gemini_service.GEMINI_CALL_TIMEOUT_SECONDS", 1):
        with patch("db.gemini_service._generate_raw_response", side_effect=lambda _: time.sleep(2)):
            from db.gemini_service import call_gemini

            with pytest.raises(ValueError, match="Gemini failed after"):
                call_gemini("prompt", retries=1)
