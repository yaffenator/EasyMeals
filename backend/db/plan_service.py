from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from google.cloud import firestore as fs
from google.cloud.firestore_v1.base_query import FieldFilter

from db.firestore_client import db
from db.diversity_service import compute_final_scores
from db.gemini_service import MealOutline
from db.gemini_service import generate_meal_details
from db.gemini_service import generate_meal_name_plan
from db.ingredient_service import get_or_create_ingredient
from db.ingredient_service import normalize_name
from db.ingredient_service import normalize_unit
from db.ingredient_service import recalculate_meal_cost


class PlanGenerationRequest(BaseModel):
    userId: str
    monthlyBudget: float = Field(ge=50, le=1000)
    weight: float = Field(ge=100, le=380)
    goalType: str
    dietaryTags: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)

    @field_validator("monthlyBudget")
    @classmethod
    def validate_budget_precision(cls, value: float) -> float:
        if not _has_max_decimals(value, 2):
            raise ValueError("monthlyBudget must have at most 2 decimal places")
        return value

    @field_validator("weight")
    @classmethod
    def validate_weight_precision(cls, value: float) -> float:
        if not _has_max_decimals(value, 1):
            raise ValueError("weight must have at most 1 decimal place")
        return value


class GenerationConflictError(ValueError):
    pass


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
    "Generate name-only meal outline (first pass).",
    "Persist generating plan with pending meals.",
    "Fill each meal details one-by-one with Gemini (second pass).",
    "Upsert ingredient prices and recalculate trusted costs per meal.",
    "Deduplicate or create recipe docs per completed meal.",
    "Update plan after each meal so frontend can unlock completed cards.",
    "Finalize grocery list and plan status.",
    "Persist users/{uid}/plans/{planId} and update mealHistory.",
]


PLAN_GENERATION_MAX_WORKERS = max(1, int(os.getenv("PLAN_GENERATION_MAX_WORKERS", "2")))
PLAN_GENERATION_EXECUTOR = ThreadPoolExecutor(max_workers=PLAN_GENERATION_MAX_WORKERS)
# Keep parallelism low: each Gemini call can take 30-90s and the API has rate limits.
# Too many concurrent calls causes queuing that pushes individual calls past the timeout.
# 3 concurrent calls with a 2s stagger between submissions is a safe default.
MEAL_DETAIL_PARALLELISM = max(1, int(os.getenv("MEAL_DETAIL_PARALLELISM", "3")))
MEAL_DETAIL_SUBMIT_STAGGER_SECONDS = float(os.getenv("MEAL_DETAIL_SUBMIT_STAGGER_SECONDS", "2.0"))
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _has_max_decimals(value: float, max_decimals: int) -> bool:
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return False
    exponent = d.as_tuple().exponent
    decimals = -exponent if exponent < 0 else 0
    return decimals <= max_decimals


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _shift_month(month_yyyy_mm: str, delta_months: int) -> str:
    year, month = [int(part) for part in month_yyyy_mm.split("-")]
    month_index = (year * 12 + (month - 1)) + delta_months
    out_year = month_index // 12
    out_month = (month_index % 12) + 1
    return f"{out_year:04d}-{out_month:02d}"


def resolve_target_month(user_id: str) -> str:
    current_month = _utcnow().strftime("%Y-%m")
    plans_ref = db.collection("users").document(user_id).collection("plans")
    ready_docs = list(plans_ref.where(filter=FieldFilter("status", "==", "ready")).stream())
    if not ready_docs:
        return current_month

    ready_months = [(doc.to_dict() or {}).get("planMonth") for doc in ready_docs]
    ready_months = [m for m in ready_months if isinstance(m, str) and len(m) == 7]
    if not ready_months:
        return _shift_month(current_month, 1)
    latest_ready_month = max(ready_months)
    base_month = max(current_month, latest_ready_month)
    return _shift_month(base_month, 1)


def get_next_plan_version(user_id: str, target_month: str) -> int:
    plans_ref = db.collection("users").document(user_id).collection("plans")
    same_month_docs = list(plans_ref.where(filter=FieldFilter("planMonth", "==", target_month)).stream())
    versions = []
    for doc in same_month_docs:
        version = (doc.to_dict() or {}).get("version")
        if isinstance(version, int):
            versions.append(version)
    return (max(versions) if versions else 0) + 1


def acquire_generation_lock(user_id: str, target_month: str, timeout_minutes: int = 10) -> tuple[str, datetime]:
    if db is None:
        raise ValueError("Firestore client is not initialized.")

    user_ref = db.collection("users").document(user_id)
    now = _utcnow()
    lock_expires_at = now + timedelta(minutes=timeout_minutes)
    request_id = uuid4().hex
    transaction = db.transaction()

    _acquire_generation_lock_txn(
        transaction,
        user_ref,
        user_id,
        request_id,
        target_month,
        now,
        lock_expires_at,
    )
    print(f"[plan_service] lock acquired user={user_id} request_id={request_id} month={target_month}")
    return request_id, lock_expires_at


def release_generation_lock(user_id: str, request_id: str, final_status: str) -> None:
    if db is None:
        return

    user_ref = db.collection("users").document(user_id)
    transaction = db.transaction()
    _release_generation_lock_txn(transaction, user_ref, request_id, final_status)
    print(f"[plan_service] lock released user={user_id} request_id={request_id} final={final_status}")


@fs.transactional
def _acquire_generation_lock_txn(
    transaction: Any,
    user_ref: Any,
    user_id: str,
    request_id: str,
    target_month: str,
    now: datetime,
    lock_expires_at: datetime,
) -> None:
    user_doc = user_ref.get(transaction=transaction)
    user_data = user_doc.to_dict() or {}
    active = user_data.get("activeGeneration") or {}
    status = active.get("status")
    expires_at = active.get("expiresAt")
    if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if status == "running" and isinstance(expires_at, datetime) and expires_at > now:
        raise GenerationConflictError("Generation already in progress for user.")

    transaction.set(
        user_ref,
        {
            "uid": user_id,
            "activeGeneration": {
                "status": "running",
                "requestId": request_id,
                "startedAt": now,
                "expiresAt": lock_expires_at,
                "targetMonth": target_month,
            },
            "updatedAt": fs.SERVER_TIMESTAMP,
            "createdAt": fs.SERVER_TIMESTAMP,
        },
        merge=True,
    )


@fs.transactional
def _release_generation_lock_txn(
    transaction: Any,
    user_ref: Any,
    request_id: str,
    final_status: str,
) -> None:
    user_doc = user_ref.get(transaction=transaction)
    active = (user_doc.to_dict() or {}).get("activeGeneration") or {}
    active_request_id = active.get("requestId")
    if active_request_id and active_request_id != request_id:
        return

    transaction.set(
        user_ref,
        {
            "activeGeneration": {
                "status": "idle",
                "requestId": request_id,
                "releasedAt": _utcnow(),
                "finalStatus": final_status,
            },
            "updatedAt": fs.SERVER_TIMESTAMP,
        },
        merge=True,
    )


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


def build_price_hint_map(ingredient_prices: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hints: dict[str, dict[str, Any]] = {}
    for ingredient_price in ingredient_prices.values():
        normalized = normalize_name(ingredient_price.name)
        hints[normalized] = {
            "category": ingredient_price.category,
            "price_value": ingredient_price.price.value,
            "price_unit": ingredient_price.price.unit,
            "default_unit": ingredient_price.defaultUnit,
            "snap_eligible": ingredient_price.snapEligible,
            "aliases": list(ingredient_price.aliases),
        }
    return hints


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


def _extract_category_from_ingredient_id(ingredient_id: str) -> str:
    if not ingredient_id.startswith("ingredient_"):
        return "uncategorized"
    parts = ingredient_id.split("_")
    return parts[-1] if len(parts) >= 3 else "uncategorized"


def _ingredient_exists(ingredient_id: str) -> bool:
    if not ingredient_id:
        return False
    return db.collection("ingredients").document(ingredient_id).get().exists


def _heal_missing_ingredient_id(
    item: dict[str, Any],
    ingredient_name_map: dict[str, str],
    price_hint_map: dict[str, dict[str, Any]],
) -> None:
    ingredient_id = item.get("ingredientId")
    if ingredient_id and _ingredient_exists(ingredient_id):
        return

    candidates = _candidate_normalized_names(item)

    for candidate_name in candidates:
        mapped = ingredient_name_map.get(candidate_name)
        if mapped and _ingredient_exists(mapped):
            item["ingredientId"] = mapped
            return

    best_name = next((c for c in candidates if c), None)
    if not best_name:
        best_name = normalize_name(str(ingredient_id or "unknown ingredient"))

    hint = price_hint_map.get(best_name, {})
    category = hint.get("category") or _extract_category_from_ingredient_id(str(ingredient_id or ""))
    unit_from_item = normalize_unit(str(item.get("unit") or "piece"))
    default_unit = hint.get("default_unit") or unit_from_item
    price_unit = hint.get("price_unit") or default_unit
    price_value = float(hint.get("price_value", 1.0))
    snap_eligible = bool(hint.get("snap_eligible", True))
    aliases = list(hint.get("aliases", []))

    healed_id = get_or_create_ingredient(
        name=best_name,
        default_unit=default_unit,
        price_value=price_value,
        price_unit=price_unit,
        category=category,
        snap_eligible=snap_eligible,
        aliases=aliases,
    )
    item["ingredientId"] = healed_id


def recalculate_meal_costs(
    meals: list[Any],
    ingredient_id_map: dict[str, str],
    ingredient_name_map: dict[str, str],
    price_hint_map: dict[str, dict[str, Any]],
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

            _heal_missing_ingredient_id(item, ingredient_name_map, price_hint_map)

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


def _flatten_weeks(weeks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for week in weeks:
        for meal in week.get("meals", []):
            flattened.append(meal)
    return flattened


def _build_placeholder_meals(plan_id: str, outlines: list[MealOutline]) -> list[dict[str, Any]]:
    placeholders: list[dict[str, Any]] = []
    for index, outline in enumerate(outlines):
        week_index = index // 7
        day_index = index % 7
        day_name = outline.day.strip() if isinstance(outline.day, str) and outline.day.strip() else DAY_NAMES[day_index]
        description = outline.description.strip() if isinstance(outline.description, str) else ""
        placeholders.append(
            {
                "id": f"{plan_id}_w{week_index + 1}_m{day_index + 1}",
                "name": outline.name,
                "day": day_name,
                "description": description,
                "mealType": outline.mealType,
                "calories": 0,
                "carbs": 0.0,
                "fat": 0.0,
                "protein": 0.0,
                "prepTime": "",
                "cookTime": "",
                "servings": 0,
                "costPerServing": 0.0,
                "difficulty": "",
                "instructions": "",
                "tags": [],
                "ingredientItems": [],
                "ingredients": [],
                "tips": [],
                "source": "generated",
                "image": "",
                "imageGenStatus": "pending",
                "status": "pending",
            }
        )
    return placeholders


def _set_plan_progress(
    user_id: str,
    plan_id: str,
    *,
    weeks: list[dict[str, Any]],
    status: str,
    failed_count: int = 0,
) -> None:
    existing_doc = db.collection("users").document(user_id).collection("plans").document(plan_id).get()
    existing_weeks = []
    if existing_doc.exists:
        existing_weeks = (existing_doc.to_dict() or {}).get("weeks") or []

    # Preserve image generation fields that may be written concurrently.
    for week_index, week in enumerate(weeks):
        meals = week.get("meals") or []
        existing_meals = []
        if week_index < len(existing_weeks):
            existing_meals = (existing_weeks[week_index] or {}).get("meals") or []
        for meal_index, meal in enumerate(meals):
            if meal_index >= len(existing_meals):
                continue
            existing_meal = existing_meals[meal_index] or {}
            for key in ("image", "imageGenStatus", "imageGenAttempts", "imageGenError"):
                if key in existing_meal and (key not in meal or meal.get(key) in (None, "")):
                    meal[key] = existing_meal.get(key)

    completed_meals = [meal for meal in _flatten_weeks(weeks) if meal.get("status") == "completed"]
    grocery_list = aggregate_grocery_list(completed_meals)
    total_meals = len(_flatten_weeks(weeks))
    progress_payload = {
        "completedMeals": len(completed_meals),
        "failedMeals": failed_count,
        "totalMeals": total_meals,
    }
    db.collection("users").document(user_id).collection("plans").document(plan_id).set(
        {
            "weeks": weeks,
            "estimatedTotalCost": _total_cost(completed_meals),
            "groceryList": [item.model_dump() for item in grocery_list],
            "status": status,
            "generationProgress": progress_payload,
            "updatedAt": fs.SERVER_TIMESTAMP,
        },
        merge=True,
    )


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

        normalized_matches = list(
            recipes_ref.where(filter=FieldFilter("normalizedName", "==", normalized_name)).limit(1).stream()
        )
        if normalized_matches:
            existing_doc = normalized_matches[0]
        else:
            exact_matches = list(recipes_ref.where(filter=FieldFilter("name", "==", recipe_name)).limit(1).stream())
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
    *,
    plan_month: str,
    version: int,
    request_id: str,
    status: str,
    superseded_by: str | None = None,
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
                "weight": request.weight,
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
        "weight": request.weight,
        "goalType": request.goalType,
        "dietaryTags": request.dietaryTags,
        "allergies": request.allergies,
        "estimatedTotalCost": estimated_total_cost,
        "status": status,
        "planMonth": plan_month,
        "version": version,
        "requestId": request_id,
        "supersededBy": superseded_by,
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


def update_plan_status(user_id: str, plan_id: str, status: str, superseded_by: str | None = None) -> None:
    payload: dict[str, Any] = {"status": status, "updatedAt": fs.SERVER_TIMESTAMP}
    if superseded_by is not None:
        payload["supersededBy"] = superseded_by
    db.collection("users").document(user_id).collection("plans").document(plan_id).set(payload, merge=True)


def supersede_ready_plans_for_month(user_id: str, plan_month: str, new_plan_id: str) -> int:
    plans_ref = db.collection("users").document(user_id).collection("plans")
    docs = list(
        plans_ref.where(filter=FieldFilter("planMonth", "==", plan_month))
        .where(filter=FieldFilter("status", "==", "ready"))
        .stream()
    )
    updated = 0
    for doc in docs:
        if doc.id == new_plan_id:
            continue
        doc.reference.set(
            {"status": "superseded", "supersededBy": new_plan_id, "updatedAt": fs.SERVER_TIMESTAMP},
            merge=True,
        )
        updated += 1
    return updated


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


def _sync_day_docs(user_id: str, plan_id: str, weeks: list[dict[str, Any]]) -> None:
    plan_ref = db.collection("users").document(user_id).collection("plans").document(plan_id)
    day_counter = 0
    for week in weeks:
        week_index = int(week.get("weekIndex", 0))
        for meal in week.get("meals", []):
            day_counter += 1
            plan_ref.collection("days").document(f"day_{day_counter:02d}").set(
                {
                    "dayIndex": day_counter,
                    "weekIndex": week_index,
                    "mealId": meal.get("id"),
                    "name": meal.get("name"),
                    "mealType": meal.get("mealType"),
                    "costPerServing": meal.get("costPerServing"),
                    "calories": meal.get("calories"),
                    "recipeRef": meal.get("recipeRef"),
                    "status": meal.get("status"),
                    "updatedAt": fs.SERVER_TIMESTAMP,
                },
                merge=True,
            )


def _normalize_tips(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _estimate_fallback_cost(monthly_budget: float) -> float:
    baseline = monthly_budget / 28.0 if monthly_budget > 0 else 4.0
    return round(max(2.5, min(baseline, 12.0)), 2)


def _build_fallback_meal(
    request: PlanGenerationRequest,
    current_meal: dict[str, Any],
    outline: MealOutline,
) -> dict[str, Any]:
    fallback_cost = _estimate_fallback_cost(request.monthlyBudget)
    calories = 550
    if request.goalType == "lose":
        calories = 430
    elif request.goalType == "gain":
        calories = 700

    return {
        **current_meal,
        "name": outline.name,
        "day": current_meal.get("day") or outline.day,
        "description": current_meal.get("description") or f"{outline.name} tailored to your preferences.",
        "mealType": outline.mealType,
        "calories": calories,
        "carbs": 55.0,
        "fat": 18.0,
        "protein": 30.0,
        "prepTime": "15 minutes",
        "cookTime": "20 minutes",
        "servings": 2,
        "costPerServing": fallback_cost,
        "difficulty": "Easy",
        "instructions": "Prepare ingredients, cook until done, and season to taste.",
        "tags": ["generated", "fallback"],
        "ingredientItems": [],
        "ingredients": [
            "1 protein portion",
            "1 vegetable portion",
            "1 carbohydrate portion",
            "Seasonings to taste",
        ],
        "tips": [
            "Adjust spices to preference.",
            "Pair with a simple side salad for extra volume.",
        ],
        "source": "generated-fallback",
        "status": "completed",
        "generationWarning": "Generated from fallback template after detail timeout/error.",
    }


def _generate_meal_detail_candidate(preferences: dict[str, Any], outline: MealOutline) -> Any:
    return generate_meal_details(preferences, outline, retries=2)


def _complete_plan_details_in_background(
    request: PlanGenerationRequest,
    preferences: dict[str, Any],
    plan_id: str,
    request_id: str,
    target_month: str,
    weeks_payload: list[dict[str, Any]],
    outlines: list[MealOutline],
    plan_started_at: datetime,
) -> None:
    lock_final_status = "failed"
    failed_count = 0

    try:
        total_meals = len(outlines)
        working_weeks = [
            {"weekIndex": int(week.get("weekIndex", 0)), "meals": [dict(meal) for meal in week.get("meals", [])]}
            for week in weeks_payload
        ]

        for index, outline in enumerate(outlines):
            print(
                f"[plan_service] request_id={request_id} stage=meal_started "
                f"index={index + 1}/{total_meals} name={outline.name}"
            )

        # Process meals in true batches: submit MEAL_DETAIL_PARALLELISM at a time,
        # wait for ALL of them to finish, then submit the next batch.
        # This ensures at most MEAL_DETAIL_PARALLELISM concurrent Gemini calls at any moment,
        # which prevents API queuing that pushes calls past the timeout window.
        def _process_batch(batch_futures: dict[Any, tuple[int, MealOutline]]) -> None:
            nonlocal failed_count
            for future in as_completed(batch_futures):
                index, outline = batch_futures[future]
                week_index = index // 7
                meal_index = index % 7
                current_meal = dict(working_weeks[week_index]["meals"][meal_index])

                try:
                    detail_response = future.result()
                    ingredient_id_map = upsert_ingredient_prices(detail_response.ingredientPrices)
                    ingredient_name_map = build_normalized_name_map(detail_response.ingredientPrices, ingredient_id_map)
                    price_hint_map = build_price_hint_map(detail_response.ingredientPrices)

                    processed_meals, _ = recalculate_meal_costs(
                        [detail_response.meal],
                        ingredient_id_map,
                        ingredient_name_map,
                        price_hint_map,
                    )
                    deduped_meals, _recipe_stats = dedupe_or_create_recipes(processed_meals)
                    completed_meal = dict(deduped_meals[0])

                    merged_meal = {
                        **current_meal,
                        **completed_meal,
                        "day": current_meal.get("day") or outline.day,
                        "description": completed_meal.get("description") or current_meal.get("description", ""),
                        "tips": _normalize_tips(completed_meal.get("tips")),
                        "status": "completed",
                    }

                    for key in ("image", "imageGenStatus", "imageGenAttempts", "imageGenError"):
                        if key in current_meal and key not in merged_meal:
                            merged_meal[key] = current_meal[key]
                        if key in current_meal and merged_meal.get(key) in (None, ""):
                            merged_meal[key] = current_meal[key]

                    # Strip Firestore DocumentReference before writing to the weeks array.
                    # Embedded references in array fields cause "even number of path elements" errors.
                    merged_meal_for_storage = {k: v for k, v in merged_meal.items() if k != "recipeRef"}
                    working_weeks[week_index]["meals"][meal_index] = merged_meal_for_storage
                    print(
                        f"[plan_service] request_id={request_id} stage=meal_completed "
                        f"index={index + 1}/{total_meals} name={outline.name}"
                    )
                except Exception as exc:
                    failed_count += 1
                    fallback_meal = _build_fallback_meal(request, current_meal, outline)
                    fallback_meal["generationError"] = str(exc)[:500]
                    fallback_meal.pop("recipeRef", None)
                    working_weeks[week_index]["meals"][meal_index] = fallback_meal
                    print(
                        f"[plan_service] request_id={request_id} stage=meal_fallback "
                        f"index={index + 1}/{total_meals} name={outline.name} error={exc}"
                    )

                _set_plan_progress(
                    request.userId,
                    plan_id,
                    weeks=working_weeks,
                    status="generating",
                    failed_count=failed_count,
                )

        # Submit and drain one batch at a time so Gemini never sees more than
        # MEAL_DETAIL_PARALLELISM concurrent requests.
        with ThreadPoolExecutor(max_workers=MEAL_DETAIL_PARALLELISM) as detail_executor:
            batch: dict[Any, tuple[int, MealOutline]] = {}
            for index, outline in enumerate(outlines):
                future = detail_executor.submit(_generate_meal_detail_candidate, preferences, outline)
                batch[future] = (index, outline)
                is_batch_full = len(batch) == MEAL_DETAIL_PARALLELISM
                is_last = index == len(outlines) - 1
                if is_batch_full or is_last:
                    batch_num = (index // MEAL_DETAIL_PARALLELISM) + 1
                    print(
                        f"[plan_service] request_id={request_id} stage=batch_start "
                        f"batch={batch_num} size={len(batch)}"
                    )
                    _process_batch(batch)
                    batch = {}
                    if not is_last:
                        time.sleep(MEAL_DETAIL_SUBMIT_STAGGER_SECONDS)

        completed_meals = [meal for meal in _flatten_weeks(working_weeks) if meal.get("status") == "completed"]
        all_completed = len(completed_meals) == len(outlines)

        if all_completed:
            superseded_count = supersede_ready_plans_for_month(request.userId, target_month, plan_id)
            meal_history_added = append_meal_history(
                user_id=request.userId,
                plan_id=plan_id,
                meals=completed_meals,
            )
            _set_plan_progress(
                request.userId,
                plan_id,
                weeks=working_weeks,
                status="ready",
                failed_count=failed_count,
            )
            _sync_day_docs(request.userId, plan_id, working_weeks)
            lock_final_status = "ready"
            total_duration_seconds = round((_utcnow() - plan_started_at).total_seconds(), 2)
            db.collection("users").document(request.userId).collection("plans").document(plan_id).set(
                {
                    "metadata": {
                        "requestId": request_id,
                        "planMonth": target_month,
                        "mealCount": len(outlines),
                        "mealHistoryAdded": meal_history_added,
                        "fallbackMealsUsed": failed_count,
                        "supersededPlansCount": superseded_count,
                        "todoFlow": TODO_FLOW,
                        "timing": {
                            "startedAt": plan_started_at.isoformat(),
                            "totalDurationSeconds": total_duration_seconds,
                        },
                    },
                    "updatedAt": fs.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            print(f"[plan_service] request_id={request_id} stage=plan_completed duration_s={total_duration_seconds}")
        else:
            _set_plan_progress(
                request.userId,
                plan_id,
                weeks=working_weeks,
                status="failed",
                failed_count=failed_count,
            )
            print(
                f"[plan_service] request_id={request_id} stage=plan_failed "
                f"reason=meal_detail_failures failed_count={failed_count}"
            )
    except Exception as exc:
        try:
            update_plan_status(request.userId, plan_id, "failed")
        except Exception:
            pass
        print(f"[plan_service] request_id={request_id} stage=plan_failed error={exc}")
    finally:
        release_generation_lock(request.userId, request_id, lock_final_status)


def _submit_plan_generation_job(
    request: PlanGenerationRequest,
    preferences: dict[str, Any],
    plan_id: str,
    request_id: str,
    target_month: str,
    weeks_payload: list[dict[str, Any]],
    outlines: list[MealOutline],
    plan_started_at: datetime,
) -> None:
    PLAN_GENERATION_EXECUTOR.submit(
        _complete_plan_details_in_background,
        request,
        preferences,
        plan_id,
        request_id,
        target_month,
        weeks_payload,
        outlines,
        plan_started_at,
    )


def generate_and_store_plan(request: PlanGenerationRequest) -> PlanGenerationResponse:
    if db is None:
        raise ValueError("Firestore client is not initialized.")

    plan_started_at = _utcnow()
    plan_id = f"plan_{uuid4().hex}"
    target_month = resolve_target_month(request.userId)
    plan_version = get_next_plan_version(request.userId, target_month)
    request_id = ""
    lock_final_status = "failed"

    try:
        request_id, _expires_at = acquire_generation_lock(request.userId, target_month, timeout_minutes=10)
    except GenerationConflictError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to acquire generation lock: {exc}") from exc

    preferences = {
        "userId": request.userId,
        "monthlyBudget": request.monthlyBudget,
        "weight": request.weight,
        "goalType": request.goalType,
        "dietaryTags": request.dietaryTags,
        "allergies": request.allergies,
    }

    try:
        first_pass_started_at = _utcnow()
        name_pass_response = generate_meal_name_plan(preferences)
        first_pass_duration_seconds = round((_utcnow() - first_pass_started_at).total_seconds(), 2)
        placeholder_meals = _build_placeholder_meals(plan_id, name_pass_response.mealPlan)
        weeks = chunk_meals_into_weeks(placeholder_meals)
        weeks_payload = [week.model_dump() for week in weeks]

        persist_user_plan(
            user_id=request.userId,
            plan_id=plan_id,
            request=request,
            weeks=weeks,
            grocery_list=[],
            estimated_total_cost=0.0,
            plan_month=target_month,
            version=plan_version,
            request_id=request_id,
            status="generating",
        )
        _set_plan_progress(
            request.userId,
            plan_id,
            weeks=weeks_payload,
            status="generating",
            failed_count=0,
        )

        _submit_plan_generation_job(
            request=request,
            preferences=preferences,
            plan_id=plan_id,
            request_id=request_id,
            target_month=target_month,
            weeks_payload=weeks_payload,
            outlines=list(name_pass_response.mealPlan),
            plan_started_at=plan_started_at,
        )

        return PlanGenerationResponse(
            userId=request.userId,
            planId=plan_id,
            status="generating",
            monthlyBudget=request.monthlyBudget,
            estimatedTotalCost=0.0,
            weeks=weeks,
            groceryList=[],
            metadata={
                "implementedStep": 2,
                "requestId": request_id,
                "planMonth": target_month,
                "planVersion": plan_version,
                "mealCount": len(name_pass_response.mealPlan),
                "planPath": f"users/{request.userId}/plans/{plan_id}",
                "todoFlow": TODO_FLOW,
                "timing": {
                    "startedAt": plan_started_at.isoformat(),
                    "firstPassDurationSeconds": first_pass_duration_seconds,
                },
            },
        )
    except Exception as exc:
        try:
            update_plan_status(request.userId, plan_id, "failed")
        except Exception:
            pass
        if request_id:
            release_generation_lock(request.userId, request_id, lock_final_status)
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Failed to generate/store plan: {exc}") from exc