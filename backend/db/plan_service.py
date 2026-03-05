from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from db.firestore_client import db
from db.gemini_service import generate_meal_plan
from db.ingredient_service import get_or_create_ingredient
from db.ingredient_service import recalculate_meal_cost


class PlanGenerationRequest(BaseModel):
    userId: str
    monthlyBudget: float
    goalType: str
    dietaryTags: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class GroceryListItem(BaseModel):
    ingredientId: str
    name: str
    totalQuantity: float
    unit: str


class PlanWeek(BaseModel):
    weekIndex: int
    meals: list[dict[str, Any]] = Field(default_factory=list)


class PlanGenerationResponse(BaseModel):
    userId: str
    planId: str
    status: str
    monthlyBudget: float
    estimatedTotalCost: float
    weeks: list[PlanWeek] = Field(default_factory=list)
    groceryList: list[GroceryListItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


TODO_FLOW = [
    "Generate validated meal plan from Gemini response schema.",
    "Upsert ingredient price entries and map ingredient ids.",
    "Recalculate all meal costs server-side.",
    "Deduplicate or create recipe documents.",
    "Apply diversity scoring to candidate meals.",
    "Enforce budget with lower-cost swaps when needed.",
    "Aggregate grocery list by ingredient and normalized unit.",
    "Persist users/{uid}/plans/{planId} and update mealHistory.",
]


def upsert_ingredient_prices(ingredient_prices: dict[str, Any]) -> dict[str, str]:
    ingredient_id_map: dict[str, str] = {}

    for source_key, ingredient_price in ingredient_prices.items():
        ingredient_id = get_or_create_ingredient(
            name=ingredient_price.name,
            default_unit=ingredient_price.defaultUnit,
            price_value=ingredient_price.price.value,
            price_unit=ingredient_price.price.unit,
            category=ingredient_price.category,
            snap_eligible=ingredient_price.snapEligible,
            aliases=list(ingredient_price.aliases),
        )
        ingredient_id_map[source_key] = ingredient_id

    return ingredient_id_map


def _meal_to_dict(meal: Any) -> dict[str, Any]:
    if hasattr(meal, "model_dump"):
        return meal.model_dump()
    if hasattr(meal, "dict"):
        return meal.dict()
    return dict(meal)


def recalculate_meal_costs(
    meals: list[Any],
    ingredient_id_map: dict[str, str],
) -> tuple[list[dict[str, Any]], float]:
    processed_meals: list[dict[str, Any]] = []
    total_estimated_cost = 0.0

    for meal in meals:
        meal_dict = _meal_to_dict(meal)
        ingredient_items = meal_dict.get("ingredientItems", [])

        for item in ingredient_items:
            source_ingredient_id = item.get("ingredientId")
            if source_ingredient_id in ingredient_id_map:
                item["ingredientId"] = ingredient_id_map[source_ingredient_id]

        trusted_cost = recalculate_meal_cost(ingredient_items)
        meal_dict["costPerServing"] = trusted_cost

        processed_meals.append(meal_dict)
        total_estimated_cost += trusted_cost

    return processed_meals, round(total_estimated_cost, 2)


def chunk_meals_into_weeks(processed_meals: list[dict[str, Any]], chunk_size: int = 7) -> list[PlanWeek]:
    weeks: list[PlanWeek] = []
    for index in range(0, len(processed_meals), chunk_size):
        week_index = index // chunk_size
        weeks.append(PlanWeek(weekIndex=week_index, meals=processed_meals[index : index + chunk_size]))
    return weeks


def generate_and_store_plan(request: PlanGenerationRequest) -> PlanGenerationResponse:
    """
    Orchestrates plan creation and persistence for a user.

    Step 2 integration:
    - Build Gemini preferences from request payload.
    - Generate and validate meal plan response via gemini_service.
    - Return a structured placeholder response until persistence steps are implemented.
    """
    if db is None:
        raise ValueError("Firestore client is not initialized.")

    preferences = {
        "userId": request.userId,
        "monthlyBudget": request.monthlyBudget,
        "goalType": request.goalType,
        "dietaryTags": request.dietaryTags,
        "allergies": request.allergies,
    }

    try:
        gemini_response = generate_meal_plan(preferences)
    except Exception as exc:
        raise ValueError(f"Failed to generate validated Gemini meal plan: {exc}") from exc

    try:
        ingredient_id_map = upsert_ingredient_prices(gemini_response.ingredientPrices)
    except Exception as exc:
        raise ValueError(f"Failed to upsert ingredient prices from Gemini response: {exc}") from exc

    try:
        processed_meals, estimated_total_cost = recalculate_meal_costs(
            gemini_response.mealPlan,
            ingredient_id_map,
        )
    except Exception as exc:
        raise ValueError(f"Failed to recalculate meal costs server-side: {exc}") from exc

    weeks = chunk_meals_into_weeks(processed_meals)

    plan_id = f"plan_{uuid4().hex}"
    return PlanGenerationResponse(
        userId=request.userId,
        planId=plan_id,
        status="costs_recalculated",
        monthlyBudget=request.monthlyBudget,
        estimatedTotalCost=estimated_total_cost,
        weeks=weeks,
        groceryList=[],
        metadata={
            "implementedStep": 4,
            "mealCount": len(gemini_response.mealPlan),
            "ingredientPriceCount": len(gemini_response.ingredientPrices),
            "ingredientMappingCount": len(ingredient_id_map),
            "ingredientIdMap": ingredient_id_map,
            "recalculatedMealCount": len(processed_meals),
            "todoFlow": TODO_FLOW,
        },
    )
