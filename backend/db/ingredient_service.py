from db.firestore_client import db
from google.cloud import firestore as fs
import math

#mapping of potential spelling of the units to the way we want to store the units
UNIT_NORMALIZATION = {
    "gram": "g", "grams": "g", "g": "g",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    "milliliter": "ml", "milliliters": "ml", "ml": "ml",
    "liter": "l", "liters": "l", "l": "l",
    "pound": "lb", "pounds": "lb", "lb": "lb",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp",
    "cup": "cup", "cups": "cup",
    "piece": "piece", "pieces": "piece",
}

MAX_PRICE_PER_UNIT_USD = 25.0
MAX_QUANTITY_BY_UNIT = {
    "g": 1000.0,
    "kg": 2.0,
    "ml": 2000.0,
    "l": 2.0,
    "oz": 64.0,
    "lb": 5.0,
    "tsp": 12.0,
    "tbsp": 16.0,
    "cup": 8.0,
    "piece": 20.0,
}

#this is to normalize ingredient names, preventing duplicates
def normalize_name(name: str) -> str:
    return name.strip().lower()

def normalize_unit(unit: str) -> str:
    return UNIT_NORMALIZATION.get(unit.strip().lower(), unit.strip().lower())

#getting an ingredient or creating one if it's not in the db already
def get_or_create_ingredient(name: str, default_unit: str, price_value: float, price_unit: str, category: str = "uncategorized", snap_eligible: bool = True, aliases: list[str] = []) -> str:
    normalized_name = normalize_name(name)
    normalized_default_unit = normalize_unit(default_unit)
    normalized_price_unit = normalize_unit(price_unit)

    ingredients_ref = db.collection("ingredients")
    #finding all documents with this ingredient name
    query = ingredients_ref.where("name", "==", normalized_name).stream()
    exists = list(query)

    if exists:
        return exists[0].id
    
    #making a robust and readable ID for each ingredient, by adding their category.
    doc_id = f"ingredient_{normalized_name.replace(' ', '_')}_{category}"

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
    '''
    We're not trusting the AI for the cost we will always call this after plan assembly
    Recalculating the total cost per serving server-side.
    '''
    total = 0.0

    for item in meal_ingredients:
        ingredient_id = item.get("ingredientId")
        try:
            quantity = float(item.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0.0
        if not math.isfinite(quantity) or quantity < 0:
            quantity = 0.0

        #this value comes from the meal's ingredient entry(array inside a meal document)... Ex -> recipe says "unit": "g" in the meal's ingredients array
        unit = normalize_unit(item.get("unit", ""))
        max_quantity = MAX_QUANTITY_BY_UNIT.get(unit)
        if max_quantity is not None:
            quantity = min(quantity, max_quantity)

        #get ingredient by id
        doc = db.collection("ingredients").document(ingredient_id).get()

        if not doc.exists:
            raise ValueError(f"Ingredient {ingredient_id} not found in database.")
        
        data = doc.to_dict()
        price_info = data.get("price", {})
        price_per_unit = price_info.get("value", 0.0)
        try:
            price_per_unit = float(price_per_unit)
        except (TypeError, ValueError):
            price_per_unit = 0.0
        if not math.isfinite(price_per_unit) or price_per_unit < 0:
            price_per_unit = 0.0
        price_per_unit = min(price_per_unit, MAX_PRICE_PER_UNIT_USD)

        stored_unit = price_info.get("unit", unit)

        #unit conversion if needed
        if unit != stored_unit:
            if unit == "g" and stored_unit == "kg":
                quantity = quantity / 1000
            elif unit == "kg" and stored_unit == "g":
                quantity = quantity * 1000
            elif unit == "lb" and stored_unit == "oz":
                quantity = quantity * 16
            elif unit == "oz" and stored_unit == "lb":
                quantity = quantity / 16
        
        total += price_per_unit * quantity
    
    return round(total, 2)
