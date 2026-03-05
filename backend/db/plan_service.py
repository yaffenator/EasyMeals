from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from google.cloud import firestore as fs

from db.firestore_client import db
from db.diversity_service import compute_final_scores
from db.gemini_service import generate_meal_plan
from db.ingredient_service import get_or_create_ingredient
from db.ingredient_service import normalize_name
from db.ingredient_service import recalculate_meal_cost


class PlanGenerationRequest(BaseModel):
    userId: str
    monthlyBudget: float = Field(gt=0)
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

        # Alias mapping: Gemini sometimes references ingredient IDs in meals as
        # ingredient_<name> while ingredientPrices may use ingredient_<name>_<category>.
        normalized_name_slug = normalize_name(ingredient_price.name).replace(" ", "_")
        ingredient_id_map.setdefault(f"ingredient_{normalized_name_slug}", ingredient_id)

        # Singular/plural alias safety:
        # e.g. ingredient_egg <-> ingredient_eggs
        if normalized_name_slug.endswith("s") and len(normalized_name_slug) > 1:
            singular = normalized_name_slug[:-1]
            ingredient_id_map.setdefault(f"ingredient_{singular}", ingredient_id)
        else:
            plural = f"{normalized_name_slug}s"
            ingredient_id_map.setdefault(f"ingredient_{plural}", ingredient_id)

    return ingredient_id_map


def build_normalized_name_map(ingredient_prices: dict[str, Any], ingredient_id_map: dict[str, str]) -> dict[str, str]:
    normalized_name_map: dict[str, str] = {}
    for source_key, ingredient_price in ingredient_prices.items():
        mapped_id = ingredient_id_map.get(source_key)
        if not mapped_id:
            continue
        normalized = normalize_name(ingredient_price.name)
        if normalized:
            normalized_name_map[normalized] = mapped_id
    return normalized_name_map


def _meal_to_dict(meal: Any) -> dict[str, Any]:
    if hasattr(meal, "model_dump"):
        return meal.model_dump()
    if hasattr(meal, "dict"):
        return meal.dict()
    return dict(meal)


def _name_from_original_text(original_text: str) -> str:
    # Remove common leading measurement patterns (e.g. "2 cups", "1/2 tsp", "3")
    text = original_text.strip().lower()
    text = re.sub(
        r"^\s*\d+(?:\.\d+)?(?:\s*/\s*\d+)?\s*(cup|cups|tbsp|tsp|oz|lb|g|kg|ml|l|piece|pieces)?\s*",
        "",
        text,
    )
    text = re.sub(r"\([^)]*\)", "", text).strip()
    return normalize_name(text)


def _candidate_normalized_names(item: dict[str, Any]) -> list[str]:
    candidates: list[str] = []

    raw_name = item.get("name")
    if isinstance(raw_name, str) and raw_name.strip():
        candidates.append(normalize_name(raw_name))

    original_text = item.get("originalText")
    if isinstance(original_text, str) and original_text.strip():
        parsed_name = _name_from_original_text(original_text)
        if parsed_name:
            candidates.append(parsed_name)

    ingredient_id = item.get("ingredientId")
    if isinstance(ingredient_id, str) and ingredient_id.startswith("ingredient_"):
        slug = ingredient_id[len("ingredient_") :].replace("_", " ").strip()
        if slug:
            candidates.append(normalize_name(slug))
            slug_parts = slug.split()
            if len(slug_parts) > 1:
                candidates.append(normalize_name(" ".join(slug_parts[:-1])))

    # preserve insertion order while removing duplicates
    return list(dict.fromkeys(candidates))


def recalculate_meal_costs(
    meals: list[Any],
    ingredient_id_map: dict[str, str],
    ingredient_name_map: dict[str, str],
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
                continue

            for candidate_name in _candidate_normalized_names(item):
                mapped_id = ingredient_name_map.get(candidate_name)
                if mapped_id:
                    item["ingredientId"] = mapped_id
                    break

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


def normalize_recipe_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def build_recipe_doc_from_meal(meal: dict[str, Any]) -> dict[str, Any]:
    recipe_name = meal.get("name", "Untitled Recipe")
    return {
        "name": recipe_name,
        "normalizedName": normalize_recipe_name(recipe_name),
        "calories": meal.get("calories", 0),
        "carbs": meal.get("carbs", 0.0),
        "fat": meal.get("fat", 0.0),
        "protein": meal.get("protein", 0.0),
        "prepTime": meal.get("prepTime", ""),
        "cookTime": meal.get("cookTime", ""),
        "servings": meal.get("servings", 1),
        "costPerServing": meal.get("costPerServing", 0.0),
        "mealType": meal.get("mealType", ""),
        "difficulty": meal.get("difficulty", ""),
        "instructions": meal.get("instructions", ""),
        "tags": meal.get("tags", []),
        "ingredientItems": meal.get("ingredientItems", []),
        "ingredients": meal.get("ingredients", []),
        "tips": meal.get("tips"),
        "source": meal.get("source", "generated"),
        "ratingCount": 0,
        "ratingSum": 0.0,
        "ratingAvg": 0.0,
        "recommendationScore": 0.0,
        "createdAt": fs.SERVER_TIMESTAMP,
        "updatedAt": fs.SERVER_TIMESTAMP,
    }


def dedupe_or_create_recipes(processed_meals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    recipes_ref = db.collection("recipes")
    deduped_meals: list[dict[str, Any]] = []
    created_count = 0
    reused_count = 0

    for meal in processed_meals:
        recipe_name = meal.get("name", "")
        normalized_name = normalize_recipe_name(recipe_name)
        existing_doc = None

        normalized_matches = list(recipes_ref.where("normalizedName", "==", normalized_name).limit(1).stream())
        if normalized_matches:
            existing_doc = normalized_matches[0]
        else:
            exact_matches = list(recipes_ref.where("name", "==", recipe_name).limit(1).stream())
            if exact_matches:
                existing_doc = exact_matches[0]

        if existing_doc:
            recipe_id = existing_doc.id
            reused_count += 1
            existing_doc.reference.set(
                {"normalizedName": normalized_name, "updatedAt": fs.SERVER_TIMESTAMP},
                merge=True,
            )
        else:
            recipe_id = f"recipe_{uuid4().hex}"
            recipe_doc = build_recipe_doc_from_meal(meal)
            recipes_ref.document(recipe_id).set(recipe_doc)
            created_count += 1

        deduped_meals.append(
            {
                **meal,
                "id": recipe_id,
                "recipeRef": recipes_ref.document(recipe_id),
            }
        )

    return deduped_meals, {"recipesCreated": created_count, "recipesReused": reused_count}


def apply_diversity_selection(
    user_id: str,
    deduped_meals: list[dict[str, Any]],
    target_count: int,
) -> tuple[list[dict[str, Any]], dict[str, int | float]]:
    candidates = [
        {
            "mealId": meal["id"],
            "recommendationScore": meal.get("recommendationScore", 0.0),
            "costPerServing": meal.get("costPerServing", 0.0),
        }
        for meal in deduped_meals
        if meal.get("id")
    ]

    scored = compute_final_scores(user_id, candidates)
    score_by_id = {entry["mealId"]: entry for entry in scored}

    enriched = []
    for meal in deduped_meals:
        score = score_by_id.get(meal.get("id"), {})
        enriched.append(
            {
                **meal,
                "diversityWeight": score.get("diversityWeight", 1.0),
                "finalScore": score.get("finalScore", meal.get("recommendationScore", 0.0)),
            }
        )

    selected = sorted(
        enriched,
        key=lambda meal: (meal.get("finalScore", 0.0), meal.get("recommendationScore", 0.0)),
        reverse=True,
    )[: min(target_count, len(enriched))]

    return selected, {"scoredCount": len(scored), "selectedCount": len(selected)}


def _total_cost(meals: list[dict[str, Any]]) -> float:
    return round(sum(float(meal.get("costPerServing", 0.0)) for meal in meals), 2)


def enforce_budget_with_swaps(
    selected_meals: list[dict[str, Any]],
    candidate_pool: list[dict[str, Any]],
    monthly_budget: float,
) -> tuple[list[dict[str, Any]], dict[str, int | float | bool]]:
    current = list(selected_meals)
    total = _total_cost(current)

    if total <= monthly_budget:
        return current, {
            "budgetExceededInitially": False,
            "swapsApplied": 0,
            "mealsDropped": 0,
            "finalTotalCost": total,
            "budgetMet": True,
        }

    swaps_applied = 0
    dropped = 0

    # First pass: swap expensive meals with cheaper alternatives not already selected.
    selected_ids = {meal.get("id") for meal in current if meal.get("id")}
    candidates_by_price = sorted(candidate_pool, key=lambda m: float(m.get("costPerServing", 0.0)))

    while total > monthly_budget:
        current_sorted = sorted(current, key=lambda m: float(m.get("costPerServing", 0.0)), reverse=True)
        if not current_sorted:
            break

        expensive = current_sorted[0]
        expensive_cost = float(expensive.get("costPerServing", 0.0))

        replacement = None
        for candidate in candidates_by_price:
            candidate_id = candidate.get("id")
            candidate_cost = float(candidate.get("costPerServing", 0.0))
            if candidate_id in selected_ids:
                continue
            if candidate_cost < expensive_cost:
                replacement = candidate
                break

        if replacement is None:
            break

        current.remove(expensive)
        current.append(replacement)
        if expensive.get("id"):
            selected_ids.discard(expensive.get("id"))
        if replacement.get("id"):
            selected_ids.add(replacement.get("id"))
        swaps_applied += 1
        total = _total_cost(current)

    # Fallback: drop highest-cost meals until budget is met (or nothing remains).
    while total > monthly_budget and current:
        current.sort(key=lambda m: float(m.get("costPerServing", 0.0)), reverse=True)
        removed = current.pop(0)
        if removed.get("id"):
            selected_ids.discard(removed.get("id"))
        dropped += 1
        total = _total_cost(current)

    return current, {
        "budgetExceededInitially": True,
        "swapsApplied": swaps_applied,
        "mealsDropped": dropped,
        "finalTotalCost": total,
        "budgetMet": total <= monthly_budget,
    }


def aggregate_grocery_list(meals: list[dict[str, Any]]) -> list[GroceryListItem]:
    aggregated: dict[tuple[str, str], dict[str, Any]] = {}

    for meal in meals:
        for item in meal.get("ingredientItems", []):
            ingredient_id = item.get("ingredientId")
            unit = item.get("unit")
            quantity = item.get("quantity", 0)

            if not ingredient_id or not unit:
                continue

            try:
                quantity_value = float(quantity)
            except (TypeError, ValueError):
                continue

            key = (ingredient_id, unit)
            if key not in aggregated:
                aggregated[key] = {
                    "ingredientId": ingredient_id,
                    "name": item.get("name") or item.get("originalText") or ingredient_id,
                    "totalQuantity": 0.0,
                    "unit": unit,
                }

            aggregated[key]["totalQuantity"] += quantity_value

    grocery_items = [
        GroceryListItem(
            ingredientId=value["ingredientId"],
            name=str(value["name"]),
            totalQuantity=round(float(value["totalQuantity"]), 2),
            unit=str(value["unit"]),
        )
        for value in aggregated.values()
    ]

    return sorted(grocery_items, key=lambda x: (x.name.lower(), x.ingredientId, x.unit))


def persist_user_plan(
    user_id: str,
    plan_id: str,
    request: PlanGenerationRequest,
    weeks: list[PlanWeek],
    grocery_list: list[GroceryListItem],
    estimated_total_cost: float,
) -> None:
    user_ref = db.collection("users").document(user_id)
    user_ref.set(
        {
            "uid": user_id,
            "mealPlanProfile": {
                "questionnaireCompleted": True,
                "allergies": request.allergies,
                "goal": request.goalType,
                "monthlyBudget": request.monthlyBudget,
                "version": 1,
                "updatedAt": fs.SERVER_TIMESTAMP,
            },
            "updatedAt": fs.SERVER_TIMESTAMP,
            "createdAt": fs.SERVER_TIMESTAMP,
        },
        merge=True,
    )

    plan_ref = user_ref.collection("plans").document(plan_id)
    weeks_payload = [week.model_dump() for week in weeks]
    plan_payload = {
        "monthlyBudget": request.monthlyBudget,
        "goalType": request.goalType,
        "dietaryTags": request.dietaryTags,
        "allergies": request.allergies,
        "estimatedTotalCost": estimated_total_cost,
        "status": "ready",
        "weeks": weeks_payload,
        "groceryList": [item.model_dump() for item in grocery_list],
        "createdAt": fs.SERVER_TIMESTAMP,
        "updatedAt": fs.SERVER_TIMESTAMP,
    }
    plan_ref.set(plan_payload)

    # Hardening: persist a day-level view so consumers can query by day without parsing weeks.
    day_counter = 0
    for week in weeks_payload:
        week_index = int(week.get("weekIndex", 0))
        for meal in week.get("meals", []):
            day_counter += 1
            day_doc_id = f"day_{day_counter:02d}"
            plan_ref.collection("days").document(day_doc_id).set(
                {
                    "dayIndex": day_counter,
                    "weekIndex": week_index,
                    "mealId": meal.get("id"),
                    "name": meal.get("name"),
                    "mealType": meal.get("mealType"),
                    "costPerServing": meal.get("costPerServing"),
                    "calories": meal.get("calories"),
                    "recipeRef": meal.get("recipeRef"),
                    "createdAt": fs.SERVER_TIMESTAMP,
                    "updatedAt": fs.SERVER_TIMESTAMP,
                }
            )


def append_meal_history(user_id: str, plan_id: str, meals: list[dict[str, Any]]) -> int:
    history_ref = db.collection("users").document(user_id).collection("mealHistory")
    created = 0

    for meal in meals:
        meal_id = meal.get("id")
        if not meal_id:
            continue
        history_ref.add(
            {
                "mealId": meal_id,
                "planId": plan_id,
                "mealName": meal.get("name"),
                "eatenAt": fs.SERVER_TIMESTAMP,
                "createdAt": fs.SERVER_TIMESTAMP,
            }
        )
        created += 1

    return created


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

    ingredient_name_map = build_normalized_name_map(gemini_response.ingredientPrices, ingredient_id_map)

    try:
        processed_meals, estimated_total_cost = recalculate_meal_costs(
            gemini_response.mealPlan,
            ingredient_id_map,
            ingredient_name_map,
        )
    except Exception as exc:
        raise ValueError(f"Failed to recalculate meal costs server-side: {exc}") from exc

    try:
        deduped_meals, recipe_stats = dedupe_or_create_recipes(processed_meals)
    except Exception as exc:
        raise ValueError(f"Failed to deduplicate or create recipes: {exc}") from exc

    try:
        selected_meals, diversity_stats = apply_diversity_selection(
            user_id=request.userId,
            deduped_meals=deduped_meals,
            target_count=len(deduped_meals),
        )
    except Exception as exc:
        raise ValueError(f"Failed to apply diversity scoring: {exc}") from exc

    try:
        budgeted_meals, budget_stats = enforce_budget_with_swaps(
            selected_meals=selected_meals,
            candidate_pool=deduped_meals,
            monthly_budget=request.monthlyBudget,
        )
    except Exception as exc:
        raise ValueError(f"Failed to enforce monthly budget: {exc}") from exc

    try:
        grocery_list = aggregate_grocery_list(budgeted_meals)
    except Exception as exc:
        raise ValueError(f"Failed to aggregate grocery list: {exc}") from exc

    final_total_cost = _total_cost(budgeted_meals)
    weeks = chunk_meals_into_weeks(budgeted_meals)

    plan_id = f"plan_{uuid4().hex}"
    try:
        persist_user_plan(
            user_id=request.userId,
            plan_id=plan_id,
            request=request,
            weeks=weeks,
            grocery_list=grocery_list,
            estimated_total_cost=final_total_cost,
        )
    except Exception as exc:
        raise ValueError(f"Failed to persist generated plan: {exc}") from exc

    try:
        meal_history_added = append_meal_history(
            user_id=request.userId,
            plan_id=plan_id,
            meals=budgeted_meals,
        )
    except Exception as exc:
        raise ValueError(f"Failed to append meal history: {exc}") from exc

    return PlanGenerationResponse(
        userId=request.userId,
        planId=plan_id,
        status="stored",
        monthlyBudget=request.monthlyBudget,
        estimatedTotalCost=final_total_cost,
        weeks=weeks,
        groceryList=grocery_list,
        metadata={
            "implementedStep": 9,
            "mealCount": len(gemini_response.mealPlan),
            "ingredientPriceCount": len(gemini_response.ingredientPrices),
            "ingredientMappingCount": len(set(ingredient_id_map.values())),
            "ingredientIdMap": ingredient_id_map,
            "recalculatedMealCount": len(processed_meals),
            "recipesCreated": recipe_stats["recipesCreated"],
            "recipesReused": recipe_stats["recipesReused"],
            "diversityScoredCount": diversity_stats["scoredCount"],
            "diversitySelectedCount": diversity_stats["selectedCount"],
            "budgetExceededInitially": budget_stats["budgetExceededInitially"],
            "budgetSwapsApplied": budget_stats["swapsApplied"],
            "budgetMealsDropped": budget_stats["mealsDropped"],
            "budgetMet": budget_stats["budgetMet"],
            "preBudgetEstimatedTotalCost": estimated_total_cost,
            "groceryItemCount": len(grocery_list),
            "mealHistoryAdded": meal_history_added,
            "planPath": f"users/{request.userId}/plans/{plan_id}",
            "todoFlow": TODO_FLOW,
        },
    )
