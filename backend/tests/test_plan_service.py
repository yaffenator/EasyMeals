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


def test_generate_and_store_plan_applies_diversity_after_recipe_dedupe():
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
                with patch(
                    "db.plan_service.get_or_create_ingredient",
                    return_value="ingredient_eggs_protein",
                ) as mock_upsert:
                    with patch(
                        "db.plan_service.recalculate_meal_cost",
                        return_value=3.75,
                    ) as mock_recalculate:
                        with patch(
                            "db.plan_service.dedupe_or_create_recipes",
                            return_value=(
                                [
                                    {
                                        "id": "recipe_123",
                                        "name": "Egg Scramble",
                                        "costPerServing": 3.75,
                                        "ingredientItems": [
                                            {
                                                "ingredientId": "ingredient_eggs_protein",
                                                "quantity": 2,
                                                "unit": "piece",
                                            }
                                        ],
                                    }
                                ],
                                {"recipesCreated": 1, "recipesReused": 0},
                            ),
                        ) as mock_dedupe:
                            with patch(
                                "db.plan_service.apply_diversity_selection",
                                return_value=(
                                    [
                                        {
                                            "id": "recipe_123",
                                            "name": "Egg Scramble",
                                            "costPerServing": 3.75,
                                            "finalScore": 1.5,
                                            "diversityWeight": 0.8,
                                        }
                                    ],
                                    {"scoredCount": 1, "selectedCount": 1},
                                ),
                            ) as mock_diversity:
                                result = generate_and_store_plan(request)

        assert result.status == "diversity_scored"
        assert result.metadata["implementedStep"] == 6
        assert result.metadata["mealCount"] == 1
        assert result.metadata["ingredientPriceCount"] == 1
        assert result.metadata["ingredientMappingCount"] == 1
        assert result.metadata["ingredientIdMap"]["ingredient_eggs_protein"] == "ingredient_eggs_protein"
        assert result.metadata["recalculatedMealCount"] == 1
        assert result.metadata["recipesCreated"] == 1
        assert result.metadata["recipesReused"] == 0
        assert result.metadata["diversityScoredCount"] == 1
        assert result.metadata["diversitySelectedCount"] == 1
        assert result.estimatedTotalCost == 3.75
        assert len(result.weeks) == 1
        assert result.weeks[0].meals[0]["id"] == "recipe_123"
        assert result.weeks[0].meals[0]["costPerServing"] == 3.75
        assert result.weeks[0].meals[0]["finalScore"] == 1.5
        mock_generate.assert_called_once()
        mock_upsert.assert_called_once_with(
            name="eggs",
            default_unit="piece",
            price_value=0.4,
            price_unit="piece",
            category="protein",
            snap_eligible=True,
            aliases=[],
        )
        mock_recalculate.assert_called_once()
        mock_dedupe.assert_called_once()
        mock_diversity.assert_called_once()


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


def test_generate_and_store_plan_wraps_ingredient_upsert_errors():
    with patch("db.firestore_client.db", MagicMock()):
        from db.gemini_service import GeminiResponse
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=250.0,
            goalType="maintain",
        )

        with patch("db.plan_service.db", MagicMock()):
            with patch(
                "db.plan_service.generate_meal_plan",
                return_value=GeminiResponse(**_valid_gemini_payload()),
            ):
                with patch("db.plan_service.get_or_create_ingredient", side_effect=ValueError("write failed")):
                    with pytest.raises(ValueError, match="Failed to upsert ingredient prices from Gemini response"):
                        generate_and_store_plan(request)


def test_generate_and_store_plan_wraps_cost_recalculation_errors():
    with patch("db.firestore_client.db", MagicMock()):
        from db.gemini_service import GeminiResponse
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=250.0,
            goalType="maintain",
        )

        with patch("db.plan_service.db", MagicMock()):
            with patch(
                "db.plan_service.generate_meal_plan",
                return_value=GeminiResponse(**_valid_gemini_payload()),
            ):
                with patch("db.plan_service.get_or_create_ingredient", return_value="ingredient_eggs_protein"):
                    with patch("db.plan_service.recalculate_meal_cost", side_effect=ValueError("bad ingredient data")):
                        with pytest.raises(ValueError, match="Failed to recalculate meal costs server-side"):
                            generate_and_store_plan(request)


def test_generate_and_store_plan_wraps_recipe_dedupe_errors():
    with patch("db.firestore_client.db", MagicMock()):
        from db.gemini_service import GeminiResponse
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=250.0,
            goalType="maintain",
        )

        with patch("db.plan_service.db", MagicMock()):
            with patch(
                "db.plan_service.generate_meal_plan",
                return_value=GeminiResponse(**_valid_gemini_payload()),
            ):
                with patch("db.plan_service.get_or_create_ingredient", return_value="ingredient_eggs_protein"):
                    with patch("db.plan_service.recalculate_meal_cost", return_value=3.75):
                        with patch("db.plan_service.dedupe_or_create_recipes", side_effect=ValueError("query failed")):
                            with pytest.raises(ValueError, match="Failed to deduplicate or create recipes"):
                                generate_and_store_plan(request)


def test_generate_and_store_plan_wraps_diversity_errors():
    with patch("db.firestore_client.db", MagicMock()):
        from db.gemini_service import GeminiResponse
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(
            userId="user_1",
            monthlyBudget=250.0,
            goalType="maintain",
        )

        with patch("db.plan_service.db", MagicMock()):
            with patch(
                "db.plan_service.generate_meal_plan",
                return_value=GeminiResponse(**_valid_gemini_payload()),
            ):
                with patch("db.plan_service.get_or_create_ingredient", return_value="ingredient_eggs_protein"):
                    with patch("db.plan_service.recalculate_meal_cost", return_value=3.75):
                        with patch(
                            "db.plan_service.dedupe_or_create_recipes",
                            return_value=([{"id": "recipe_123", "name": "Egg Scramble"}], {"recipesCreated": 0, "recipesReused": 1}),
                        ):
                            with patch("db.plan_service.apply_diversity_selection", side_effect=ValueError("history query failed")):
                                with pytest.raises(ValueError, match="Failed to apply diversity scoring"):
                                    generate_and_store_plan(request)
