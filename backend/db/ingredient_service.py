from db.firestore_client import db
from google.cloud import firestore as fs
import json
import math
import os

# ---------------------------------------------------------------------------
# accurate_ingredients.json is the single source of truth for prices.
# Loaded once at startup — no Firestore reads needed for cost calculation.
# ---------------------------------------------------------------------------
def _load_master_prices() -> dict[str, dict]:
    """
    Load and flatten accurate_ingredients.json into a single id->data dict.
    Also builds a name->id reverse lookup for fuzzy fallback matching.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Walk up to find the file — it lives one level above the db/ package
    for path in [
        os.path.join(base_dir, "..", "accurate_ingredients.json"),
        os.path.join(base_dir, "accurate_ingredients.json"),
    ]:
        if os.path.exists(path):
            with open(path, "r") as f:
                nested = json.load(f)
            flat: dict[str, dict] = {}
            for _category, items in nested.items():
                for key, data in items.items():
                    flat[key] = data
            return flat
    raise FileNotFoundError("accurate_ingredients.json not found")


# Loaded once at module import — fast dict lookup for every cost calculation
MASTER_PRICES: dict[str, dict] = _load_master_prices()

# Reverse lookup: ingredient name (lowercase) -> master ID
_NAME_TO_ID: dict[str, str] = {
    data["name"].lower(): key for key, data in MASTER_PRICES.items()
}
# Also index by key-as-words (broccoli_florets -> "broccoli florets")
for _k in list(MASTER_PRICES.keys()):
    _NAME_TO_ID.setdefault(_k.replace("_", " "), _k)

# Category suffixes appended by get_or_create_ingredient to Firestore doc IDs.
# Used to strip them when resolving Firestore IDs back to JSON keys.
_FIRESTORE_CATEGORY_SUFFIXES: list[str] = [
    "_meat", "_poultry", "_vegetables", "_produce", "_grains",
    "_dairy", "_pantry", "_seafood", "_canned goods", "_canned_goods",
    "_uncategorized",
]


def _resolve_to_master_id(ingredient_id: str) -> str | None:
    """
    Resolve any ingredient ID format to a MASTER_PRICES key.

    Handles three formats:
      1. JSON key directly:      "broccoli_florets"
      2. Firestore doc ID:       "ingredient_broccoli_florets_vegetables"
      3. Gemini invented ID:     "chicken_breast" (no suffix)

    Returns the matching MASTER_PRICES key, or None if unresolvable.
    """
    # 1. Direct match
    if ingredient_id in MASTER_PRICES:
        return ingredient_id

    # 2. Strip "ingredient_" prefix if present
    name_part = ingredient_id
    if name_part.startswith("ingredient_"):
        name_part = name_part[len("ingredient_"):]

    # 3. Strip known category suffixes
    for suffix in _FIRESTORE_CATEGORY_SUFFIXES:
        if name_part.endswith(suffix):
            name_part = name_part[: -len(suffix)]
            break

    # 4. Try stripped value as a direct JSON key
    if name_part in MASTER_PRICES:
        return name_part

    # 5. Try name lookup (underscore->space)
    name_spaced = name_part.replace("_", " ")
    found = _NAME_TO_ID.get(name_spaced)
    if found:
        return found

    # 6. Substring match as last resort (e.g. "top_sirloin_steak" in "beef_sirloin_steak")
    for key in MASTER_PRICES:
        if name_part in key or key in name_part:
            return key

    return None

# mapping of potential spelling of the units to the way we want to store the units
UNIT_NORMALIZATION = {
    "gram": "g", "grams": "g", "g": "g",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    "milliliter": "ml", "milliliters": "ml", "ml": "ml",
    "liter": "l", "liters": "l", "l": "l",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp",
    "cup": "cup", "cups": "cup",
    "piece": "piece", "pieces": "piece",
    "each": "each",
    "clove": "clove", "cloves": "clove",
    "can": "can", "cans": "can",
    "slice": "slice", "slices": "slice",
    "pack": "pack",
    "bunch": "bunch",
    "head": "head",
    "tub": "tub",
    "jar": "jar",
    "loaf": "loaf",
}

MAX_PRICE_PER_UNIT_USD = 25.0
MAX_QUANTITY_BY_UNIT = {
    "g": 1000.0, "kg": 2.0, "ml": 2000.0, "l": 2.0,
    "oz": 64.0, "lb": 5.0, "tsp": 48.0, "tbsp": 32.0,
    "cup": 8.0, "piece": 20.0, "each": 20.0,
    "clove": 12.0, "can": 4.0, "slice": 16.0,
}


def normalize_name(name: str) -> str:
    return name.strip().lower()

def normalize_unit(unit: str) -> str:
    return UNIT_NORMALIZATION.get(unit.strip().lower(), unit.strip().lower())


def get_or_create_ingredient(
    name: str,
    default_unit: str,
    price_value: float,
    price_unit: str,
    category: str = "uncategorized",
    snap_eligible: bool = True,
    aliases: list[str] = [],
) -> str:
    """
    Upsert an ingredient doc in Firestore for reference/history purposes.
    Price stored here is from the master JSON, not from Gemini.
    Cost calculations never read from this — they use MASTER_PRICES directly.
    """
    normalized_name = normalize_name(name)
    normalized_default_unit = normalize_unit(default_unit)
    normalized_price_unit = normalize_unit(price_unit)

    # Check if a master price entry exists for this name and use that price instead
    master_entry = _NAME_TO_ID.get(normalized_name)
    if master_entry and master_entry in MASTER_PRICES:
        master = MASTER_PRICES[master_entry]
        price_value = master["price"]
        normalized_price_unit = normalize_unit(master["unit"])
        normalized_default_unit = normalized_price_unit

    ingredients_ref = db.collection("ingredients")
    query = ingredients_ref.where("name", "==", normalized_name).stream()
    exists = list(query)
    if exists:
        return exists[0].id

    doc_id = f"ingredient_{normalized_name.replace(chr(32), chr(95))}_{category}"
    doc_ref = ingredients_ref.document(doc_id)
    doc_ref.set({
        "name": normalized_name,
        "aliases": aliases,
        "category": category,
        "defaultUnit": normalized_default_unit,
        "snapEligible": snap_eligible,
        "price": {
            "value": price_value,
            "currency": "USD",
            "unitQuantity": 1,
            "unit": normalized_price_unit,
        },
        "createdAt": fs.SERVER_TIMESTAMP,
        "updatedAt": fs.SERVER_TIMESTAMP,
    })
    return doc_id


def recalculate_meal_cost(meal_ingredients: list[dict]) -> float:
    """
    Calculate total cost per serving using MASTER_PRICES (accurate_ingredients.json).
    Never reads from Firestore — Firestore prices come from Gemini and cannot be trusted.

    Resolution order per ingredient:
      1. Direct ID match in MASTER_PRICES
      2. Name match via _NAME_TO_ID reverse lookup
      3. Falls back to 0.0 with a warning (add missing ingredient to accurate_ingredients.json)
    """
    total = 0.0

    for item in meal_ingredients:
        ingredient_id = item.get("ingredientId", "")
        try:
            quantity = float(item.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0.0
        if not math.isfinite(quantity) or quantity < 0:
            quantity = 0.0

        unit = normalize_unit(item.get("unit", ""))
        max_quantity = MAX_QUANTITY_BY_UNIT.get(unit)
        if max_quantity is not None:
            quantity = min(quantity, max_quantity)

        # Resolve whatever ID format was stored (JSON key, Firestore doc ID, or Gemini variant)
        resolved_id = _resolve_to_master_id(ingredient_id)
        if resolved_id and resolved_id != ingredient_id:
            print(f"[ingredient_service] INFO: resolved '{ingredient_id}' -> '{resolved_id}'")
        master = MASTER_PRICES.get(resolved_id) if resolved_id else None

        if master is None:
            print(f"[ingredient_service] WARN: no master price for '{ingredient_id}' — add to accurate_ingredients.json")
            continue

        price_per_unit = float(master["price"])
        price_per_unit = min(price_per_unit, MAX_PRICE_PER_UNIT_USD)

        total += price_per_unit * quantity

    return round(total, 2)