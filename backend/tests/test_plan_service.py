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


def test_generate_and_store_plan_enforces_budget_after_diversity():
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
                                with patch(
                                    "db.plan_service.enforce_budget_with_swaps",
                                    return_value=(
                                        [
                                            {
                                                "id": "recipe_123",
                                                "name": "Egg Scramble",
                                                "costPerServing": 3.25,
                                                "finalScore": 1.5,
                                                "diversityWeight": 0.8,
                                                "ingredientItems": [
                                                    {
                                                        "ingredientId": "ingredient_eggs_protein",
                                                        "originalText": "2 eggs",
                                                        "quantity": 2,
                                                        "unit": "piece",
                                                    },
                                                    {
                                                        "ingredientId": "ingredient_eggs_protein",
                                                        "originalText": "1 egg",
                                                        "quantity": 1,
                                                        "unit": "piece",
                                                    },
                                                ],
                                            }
                                        ],
                                        {
                                            "budgetExceededInitially": True,
                                            "swapsApplied": 1,
                                            "mealsDropped": 0,
                                            "finalTotalCost": 3.25,
                                            "budgetMet": True,
                                        },
                                    ),
                                ) as mock_budget:
                                    with patch("db.plan_service.persist_user_plan") as mock_persist_plan:
                                        with patch("db.plan_service.append_meal_history", return_value=1) as mock_history:
                                            result = generate_and_store_plan(request)

        assert result.status == "stored"
        assert result.metadata["implementedStep"] == 9
        assert result.metadata["mealCount"] == 1
        assert result.metadata["ingredientPriceCount"] == 1
        assert result.metadata["ingredientMappingCount"] == 1
        assert result.metadata["ingredientIdMap"]["ingredient_eggs_protein"] == "ingredient_eggs_protein"
        assert result.metadata["recalculatedMealCount"] == 1
        assert result.metadata["recipesCreated"] == 1
        assert result.metadata["recipesReused"] == 0
        assert result.metadata["diversityScoredCount"] == 1
        assert result.metadata["diversitySelectedCount"] == 1
        assert result.metadata["budgetExceededInitially"] is True
        assert result.metadata["budgetSwapsApplied"] == 1
        assert result.metadata["budgetMealsDropped"] == 0
        assert result.metadata["budgetMet"] is True
        assert result.metadata["preBudgetEstimatedTotalCost"] == 3.75
        assert result.metadata["groceryItemCount"] == 1
        assert result.metadata["mealHistoryAdded"] == 1
        assert result.metadata["planPath"].startswith("users/user_1/plans/plan_")
        assert result.estimatedTotalCost == 3.25
        assert len(result.weeks) == 1
        assert result.weeks[0].meals[0]["id"] == "recipe_123"
        assert result.weeks[0].meals[0]["costPerServing"] == 3.25
        assert result.weeks[0].meals[0]["finalScore"] == 1.5
        assert len(result.groceryList) == 1
        assert result.groceryList[0].ingredientId == "ingredient_eggs_protein"
        assert result.groceryList[0].unit == "piece"
        assert result.groceryList[0].totalQuantity == 3.0
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
        mock_budget.assert_called_once()
        mock_persist_plan.assert_called_once()
        mock_history.assert_called_once()


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


def test_generate_and_store_plan_wraps_budget_enforcement_errors():
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
                            with patch(
                                "db.plan_service.apply_diversity_selection",
                                return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"scoredCount": 1, "selectedCount": 1}),
                            ):
                                with patch("db.plan_service.enforce_budget_with_swaps", side_effect=ValueError("swap strategy failed")):
                                    with pytest.raises(ValueError, match="Failed to enforce monthly budget"):
                                        generate_and_store_plan(request)


def test_generate_and_store_plan_wraps_grocery_aggregation_errors():
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
                            with patch(
                                "db.plan_service.apply_diversity_selection",
                                return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"scoredCount": 1, "selectedCount": 1}),
                            ):
                                with patch(
                                    "db.plan_service.enforce_budget_with_swaps",
                                    return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"budgetExceededInitially": False, "swapsApplied": 0, "mealsDropped": 0, "finalTotalCost": 3.75, "budgetMet": True}),
                                ):
                                    with patch("db.plan_service.aggregate_grocery_list", side_effect=ValueError("aggregate failed")):
                                        with pytest.raises(ValueError, match="Failed to aggregate grocery list"):
                                            generate_and_store_plan(request)


def test_generate_and_store_plan_wraps_plan_persistence_errors():
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
                            with patch(
                                "db.plan_service.apply_diversity_selection",
                                return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"scoredCount": 1, "selectedCount": 1}),
                            ):
                                with patch(
                                    "db.plan_service.enforce_budget_with_swaps",
                                    return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"budgetExceededInitially": False, "swapsApplied": 0, "mealsDropped": 0, "finalTotalCost": 3.75, "budgetMet": True}),
                                ):
                                    with patch("db.plan_service.aggregate_grocery_list", return_value=[]):
                                        with patch("db.plan_service.persist_user_plan", side_effect=ValueError("write failed")):
                                            with pytest.raises(ValueError, match="Failed to persist generated plan"):
                                                generate_and_store_plan(request)


def test_enforce_budget_with_swaps_keeps_selection_when_under_budget():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import enforce_budget_with_swaps

        selected = [
            {"id": "r1", "name": "A", "costPerServing": 2.0},
            {"id": "r2", "name": "B", "costPerServing": 3.0},
        ]
        result, stats = enforce_budget_with_swaps(selected, selected, monthly_budget=10.0)

        assert len(result) == 2
        assert stats["budgetExceededInitially"] is False
        assert stats["swapsApplied"] == 0
        assert stats["mealsDropped"] == 0
        assert stats["budgetMet"] is True
        assert stats["finalTotalCost"] == 5.0


def test_enforce_budget_with_swaps_replaces_expensive_meal_when_possible():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import enforce_budget_with_swaps

        selected = [
            {"id": "r_exp", "name": "Expensive", "costPerServing": 8.0},
            {"id": "r_mid", "name": "Mid", "costPerServing": 4.0},
        ]
        pool = selected + [{"id": "r_cheap", "name": "Cheap", "costPerServing": 1.5}]

        result, stats = enforce_budget_with_swaps(selected, pool, monthly_budget=9.0)
        ids = {meal["id"] for meal in result}

        assert "r_cheap" in ids
        assert "r_exp" not in ids
        assert stats["budgetExceededInitially"] is True
        assert stats["swapsApplied"] == 1
        assert stats["budgetMet"] is True
        assert stats["finalTotalCost"] <= 9.0


def test_enforce_budget_with_swaps_drops_meals_when_no_replacement_exists():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import enforce_budget_with_swaps

        selected = [
            {"id": "r1", "name": "A", "costPerServing": 7.0},
            {"id": "r2", "name": "B", "costPerServing": 6.0},
        ]

        result, stats = enforce_budget_with_swaps(selected, selected, monthly_budget=5.0)

        assert len(result) <= 1
        assert stats["budgetExceededInitially"] is True
        assert stats["swapsApplied"] == 0
        assert stats["mealsDropped"] >= 1
        assert stats["budgetMet"] is True
        assert stats["finalTotalCost"] <= 5.0


def test_aggregate_grocery_list_groups_by_ingredient_and_unit():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import aggregate_grocery_list

        meals = [
            {
                "ingredientItems": [
                    {"ingredientId": "ing_eggs", "originalText": "2 eggs", "quantity": 2, "unit": "piece"},
                    {"ingredientId": "ing_milk", "originalText": "200 ml milk", "quantity": 200, "unit": "ml"},
                ]
            },
            {
                "ingredientItems": [
                    {"ingredientId": "ing_eggs", "originalText": "1 egg", "quantity": 1, "unit": "piece"},
                    {"ingredientId": "ing_milk", "originalText": "0.5 l milk", "quantity": 0.5, "unit": "l"},
                ]
            },
        ]

        result = aggregate_grocery_list(meals)
        by_key = {(item.ingredientId, item.unit): item.totalQuantity for item in result}

        assert by_key[("ing_eggs", "piece")] == 3.0
        assert by_key[("ing_milk", "ml")] == 200.0
        assert by_key[("ing_milk", "l")] == 0.5


def test_apply_diversity_selection_sorts_by_final_score():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import apply_diversity_selection

        deduped_meals = [
            {"id": "r1", "name": "A", "recommendationScore": 1.0},
            {"id": "r2", "name": "B", "recommendationScore": 1.0},
        ]

        scored_payload = [
            {"mealId": "r1", "diversityWeight": 0.5, "finalScore": 0.5},
            {"mealId": "r2", "diversityWeight": 0.9, "finalScore": 0.9},
        ]

        with patch("db.plan_service.compute_final_scores", return_value=scored_payload):
            selected, stats = apply_diversity_selection("user_1", deduped_meals, target_count=1)

        assert len(selected) == 1
        assert selected[0]["id"] == "r2"
        assert selected[0]["finalScore"] == 0.9
        assert stats["scoredCount"] == 2
        assert stats["selectedCount"] == 1


def test_recalculate_meal_costs_reconciles_by_normalized_ingredient_name():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import recalculate_meal_costs

        meals = [
            {
                "name": "Egg Scramble",
                "ingredientItems": [
                    {
                        "ingredientId": "ingredient_egg",
                        "originalText": "2 eggs",
                        "quantity": 2,
                        "unit": "piece",
                    }
                ],
            }
        ]
        ingredient_id_map = {"ingredient_eggs_protein": "ingredient_eggs_protein"}
        ingredient_name_map = {"eggs": "ingredient_eggs_protein"}
        price_hint_map = {}

        with patch("db.plan_service.recalculate_meal_cost", return_value=1.2):
            with patch("db.plan_service._ingredient_exists", return_value=True):
                processed, total = recalculate_meal_costs(
                    meals,
                    ingredient_id_map,
                    ingredient_name_map,
                    price_hint_map,
                )

        assert processed[0]["ingredientItems"][0]["ingredientId"] == "ingredient_eggs_protein"
        assert processed[0]["costPerServing"] == 1.2
        assert total == 1.2


def test_recalculate_meal_costs_auto_creates_missing_ingredient_doc():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import recalculate_meal_costs

        meals = [
            {
                "name": "Potato Mash",
                "ingredientItems": [
                    {
                        "ingredientId": "ingredient_potatoes_vegetable",
                        "originalText": "2 cups potatoes",
                        "quantity": 2,
                        "unit": "cup",
                    }
                ],
            }
        ]
        ingredient_id_map = {}
        ingredient_name_map = {}
        price_hint_map = {}

        with patch("db.plan_service._ingredient_exists", return_value=False):
            with patch("db.plan_service.get_or_create_ingredient", return_value="ingredient_potatoes_uncategorized"):
                with patch("db.plan_service.recalculate_meal_cost", return_value=4.0):
                    processed, total = recalculate_meal_costs(
                        meals,
                        ingredient_id_map,
                        ingredient_name_map,
                        price_hint_map,
                    )

        assert processed[0]["ingredientItems"][0]["ingredientId"] == "ingredient_potatoes_uncategorized"
        assert processed[0]["costPerServing"] == 4.0
        assert total == 4.0


def test_generate_and_store_plan_wraps_meal_history_errors():
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
                            with patch(
                                "db.plan_service.apply_diversity_selection",
                                return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"scoredCount": 1, "selectedCount": 1}),
                            ):
                                with patch(
                                    "db.plan_service.enforce_budget_with_swaps",
                                    return_value=([{"id": "recipe_123", "name": "Egg Scramble", "costPerServing": 3.75}], {"budgetExceededInitially": False, "swapsApplied": 0, "mealsDropped": 0, "finalTotalCost": 3.75, "budgetMet": True}),
                                ):
                                    with patch("db.plan_service.aggregate_grocery_list", return_value=[]):
                                        with patch("db.plan_service.persist_user_plan"):
                                            with patch("db.plan_service.append_meal_history", side_effect=ValueError("history failed")):
                                                with pytest.raises(ValueError, match="Failed to append meal history"):
                                                    generate_and_store_plan(request)
