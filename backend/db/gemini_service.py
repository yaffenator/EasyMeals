import json
import os
import re
import threading
from typing import Any, Optional, TypeVar

from pydantic import BaseModel, Field

GEMINI_MODEL = "gemini-3-flash-preview"
# Retries for the detail pass: 2 is enough. Each timeout costs the full timeout window,
# so 3 retries x 90s = 270s per meal worst case — much better than 3 x 150s = 450s.
DEFAULT_RETRIES = 2
# 90s is sufficient for a single-meal detail prompt with a focused ingredient subset.
# The old 150s default was sized for the full-plan prompt which no longer exists.
GEMINI_CALL_TIMEOUT_SECONDS = max(60, int(os.getenv("GEMINI_CALL_TIMEOUT_SECONDS", "90")))
# Short timeout for the name-pass (28 meal outlines only, no prices or instructions).
GEMINI_NAME_PASS_TIMEOUT_SECONDS = max(30, int(os.getenv("GEMINI_NAME_PASS_TIMEOUT_SECONDS", "60")))
# Backoff between retries so a rate-limited API has time to recover.
GEMINI_RETRY_BACKOFF_SECONDS = float(os.getenv("GEMINI_RETRY_BACKOFF_SECONDS", "3.0"))

# ---------------------------------------------------------------------------
# Keyword → ingredient ID map.
# Keys match the meal name/description; values are exact IDs from accurate_ingredients.json.
# Used to pass a focused ~25-entry subset to each prompt instead of the full file,
# which prevents Gemini from hallucinating or renaming ingredient IDs.
# ---------------------------------------------------------------------------
KEYWORD_MAP: dict[str, list[str]] = {
    "beef":         ["beef_ground_90_10", "beef_sirloin_steak", "beef_chuck_roast"],
    "steak":        ["beef_sirloin_steak"],
    "ground beef":  ["beef_ground_90_10"],
    "meatball":     ["beef_ground_90_10", "pork_ground"],
    "pork":         ["pork_chops_boneless", "pork_tenderloin", "pork_ground"],
    "bacon":        ["bacon_sliced"],
    "sausage":      ["sausage_italian"],
    "chicken":      ["chicken_breast_boneless", "chicken_thighs_boneless", "chicken_thighs_bonein"],
    "turkey":       ["turkey_ground"],
    "salmon":       ["salmon_fillet"],
    "tilapia":      ["tilapia_fillet"],
    "shrimp":       ["shrimp_frozen_peeled"],
    "tuna":         ["tuna_canned"],
    "cod":          ["cod_fillet"],
    "fish":         ["salmon_fillet", "tilapia_fillet", "cod_fillet"],
    "seafood":      ["shrimp_frozen_peeled", "salmon_fillet"],
    "broccoli":     ["broccoli_florets"],
    "carrot":       ["carrots_whole"],
    "spinach":      ["spinach_fresh"],
    "kale":         ["kale"],
    "bell pepper":  ["bell_pepper_red", "bell_pepper_green"],
    "pepper":       ["bell_pepper_red", "bell_pepper_green"],
    "onion":        ["onion_yellow", "onion_red"],
    "potato":       ["potato_russet", "potato_sweet"],
    "sweet potato": ["potato_sweet"],
    "zucchini":     ["zucchini"],
    "tomato":       ["tomato_roma", "diced_tomatoes_canned"],
    "asparagus":    ["asparagus"],
    "cauliflower":  ["cauliflower"],
    "cabbage":      ["cabbage_green"],
    "rice":         ["rice_white_jasmine", "rice_brown"],
    "quinoa":       ["quinoa"],
    "pasta":        ["pasta_spaghetti", "pasta_penne"],
    "spaghetti":    ["pasta_spaghetti"],
    "penne":        ["pasta_penne"],
    "noodle":       ["pasta_spaghetti", "pasta_penne"],
    "oat":          ["oats_rolled"],
    "bread":        ["bread_whole_wheat"],
    "tortilla":     ["tortillas_corn", "tortillas_flour"],
    "taco":         ["tortillas_corn", "tortillas_flour"],
    "burrito":      ["tortillas_flour"],
    "wrap":         ["tortillas_flour"],
    "egg":          ["eggs_large"],
    "milk":         ["milk_whole"],
    "butter":       ["butter_unsalted"],
    "cheese":       ["cheese_cheddar_shredded", "cheese_parmesan"],
    "cheddar":      ["cheese_cheddar_shredded"],
    "parmesan":     ["cheese_parmesan"],
    "yogurt":       ["yogurt_greek_plain"],
    # Pantry — oils, sauces, condiments
    "olive oil":       ["olive_oil_evoo"],
    "oil":             ["olive_oil_evoo", "vegetable_oil"],
    "soy sauce":       ["soy_sauce"],
    "worcestershire":  ["worcestershire"],
    "bbq":             ["bbq_sauce"],
    "pesto":           ["pesto_jarred"],
    "salsa":           ["salsa_jarred"],
    "hot sauce":       ["hot_sauce"],
    "wine":            ["white_wine"],
    "vinegar":         ["apple_cider_vinegar"],
    "honey":           ["honey"],
    "glaze":           ["honey", "soy_sauce"],
    # Canned / jarred
    "black bean":      ["black_beans_canned"],
    "kidney bean":     ["kidney_beans_canned"],
    "refried":         ["refried_beans_canned"],
    "chickpea":        ["chickpeas_canned"],
    "bean":            ["black_beans_canned", "kidney_beans_canned", "chickpeas_canned"],
    "tomato paste":    ["tomato_paste"],
    "tomato sauce":    ["tomato_sauce_canned", "crushed_tomatoes"],
    "crushed tomato":  ["crushed_tomatoes"],
    "diced tomato":    ["diced_tomatoes_canned"],
    "coconut milk":    ["coconut_milk_canned"],
    "refried beans":   ["refried_beans_canned"],
    # Broths
    "chicken broth":   ["chicken_broth"],
    "vegetable broth": ["vegetable_broth"],
    "beef broth":      ["beef_broth"],
    "broth":           ["chicken_broth", "vegetable_broth"],
    # Dairy extras
    "cream":           ["cream_heavy"],
    "heavy cream":     ["cream_heavy"],
    "alfredo":         ["cream_heavy", "cheese_parmesan", "butter_unsalted"],
    "mozzarella":      ["cheese_mozzarella"],
    "feta":            ["cheese_feta"],
    "ricotta":         ["cheese_ricotta"],
    "sour cream":      ["sour_cream"],
    "cream cheese":    ["cream_cheese"],
    # Spices
    "italian":         ["italian_seasoning"],
    "cumin":           ["cumin_ground"],
    "chili":           ["chili_powder"],
    "paprika":         ["paprika"],
    "oregano":         ["oregano_dried"],
    "curry powder":    ["curry_powder"],
    "garam masala":    ["garam_masala"],
    # Produce extras
    "mushroom":        ["mushrooms_cremini", "mushrooms_white"],
    "pea":             ["peas_frozen"],
    "corn":            ["corn_frozen"],
    "green bean":      ["green_beans_fresh"],
    "celery":          ["celery"],
    "eggplant":        ["eggplant"],
    "lemon":           ["lemon"],
    "lime":            ["lime"],
    "jalapeno":        ["jalapeno"],
    # Grains extras
    "linguine":        ["pasta_linguine"],
    "fettuccine":      ["pasta_fettuccine"],
    "rotini":          ["pasta_rotini"],
    "arborio":         ["rice_arborio"],
    "risotto":         ["rice_arborio", "mushrooms_cremini", "cheese_parmesan", "white_wine"],
    "lentil":          ["lentils_green", "lentils_red"],
    "breadcrumb":      ["breadcrumbs"],
    "pizza":           ["pizza_dough", "cheese_mozzarella", "tomato_sauce_canned"],
    "flour":           ["flour_all_purpose"],
    # Combo meal keywords
    "stir fry":        ["soy_sauce", "vegetable_oil", "rice_white_jasmine"],
    "fried rice":      ["soy_sauce", "vegetable_oil", "rice_white_jasmine", "eggs_large"],
    "curry":           ["curry_powder", "coconut_milk_canned", "diced_tomatoes_canned", "rice_white_jasmine"],
    "soup":            ["chicken_broth", "carrots_whole", "onion_yellow", "celery"],
    "taco":            ["tortillas_corn", "salsa_jarred", "sour_cream"],
    "quesadilla":      ["tortillas_flour", "cheese_cheddar_shredded", "salsa_jarred"],
    "casserole":       ["cream_heavy", "chicken_broth", "breadcrumbs"],
    "shepherd":        ["beef_broth", "peas_frozen", "potato_russet"],
    "peanut":          ["peanut_butter"],
    "bbq pulled":      ["bbq_sauce", "pork_tenderloin"],
    "kabob":           ["bell_pepper_red", "onion_yellow", "zucchini"],
    "minestrone":      ["vegetable_broth", "diced_tomatoes_canned", "kidney_beans_canned", "pasta_rotini"],
}

_ALWAYS_INCLUDE: list[str] = [
    "olive_oil_evoo", "vegetable_oil", "garlic_clove", "onion_yellow",
    "chicken_broth", "tomato_paste", "soy_sauce", "eggs_large", "butter_unsalted",
    "italian_seasoning", "cumin_ground", "chili_powder",
]

_FALLBACK_PADDING: list[str] = [
    "bell_pepper_red", "carrots_whole", "broccoli_florets", "potato_russet",
    "rice_white_jasmine", "pasta_penne", "cheese_cheddar_shredded", "milk_whole",
    "black_beans_canned", "diced_tomatoes_canned", "lemon", "onion_red",
]


def _select_relevant_ingredients(meal_name: str, meal_description: str, all_ingredients: dict) -> dict:
    """Return a focused ~25-35 entry subset of all_ingredients relevant to this meal."""
    search_text = f"{meal_name} {meal_description}".lower()
    relevant_keys: set[str] = set(_ALWAYS_INCLUDE)

    for keyword, ids in KEYWORD_MAP.items():
        if keyword in search_text:
            relevant_keys.update(ids)

    for key in _FALLBACK_PADDING:
        if len(relevant_keys) >= 32:
            break
        relevant_keys.add(key)

    return {k: all_ingredients[k] for k in relevant_keys if k in all_ingredients}


class IngredientItem(BaseModel):
    ingredientId: str
    originalText: str
    quantity: float
    unit: str
    notes: Optional[str] = ""


class Meal(BaseModel):
    name: str
    calories: int
    carbs: float
    fat: float
    protein: float
    prepTime: str
    cookTime: str
    servings: int
    costPerServing: float
    mealType: str
    difficulty: str
    instructions: str
    tags: list[str]
    ingredientItems: list[IngredientItem]
    ingredients: list[str]
    tips: Optional[str] = None
    source: Optional[str] = "generated"


class PriceMap(BaseModel):
    value: float
    currency: str = "USD"
    unitQuantity: float = 1.0
    unit: str


class IngredientPrice(BaseModel):
    name: str
    category: str
    defaultUnit: str
    price: PriceMap
    snapEligible: bool = True
    aliases: list[str] = Field(default_factory=list)


class GeminiResponse(BaseModel):
    mealPlan: list[Meal]
    ingredientPrices: dict[str, IngredientPrice]


class MealOutline(BaseModel):
    name: str
    mealType: str
    day: str
    description: str = ""


class MealNamePlanResponse(BaseModel):
    mealPlan: list[MealOutline]


class MealDetailResponse(BaseModel):
    meal: Meal
    ingredientPrices: dict[str, IngredientPrice]


TModel = TypeVar("TModel", bound=BaseModel)


def _run_with_timeout(func: Any, *args: Any, timeout_seconds: int) -> Any:
    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}
    done = threading.Event()

    def target() -> None:
        try:
            result["value"] = func(*args)
        except BaseException as exc:  # noqa: BLE001
            error["exc"] = exc
        finally:
            done.set()

    worker = threading.Thread(target=target, daemon=True)
    worker.start()

    if not done.wait(timeout_seconds):
        raise TimeoutError(f"Gemini call timed out after {timeout_seconds} seconds")

    if "exc" in error:
        raise error["exc"]
    return result.get("value")


def _normalize_instruction_text(value: str) -> str:
    text = " ".join((value or "").replace("\n", " ").split())
    if not text:
        return ""

    numbered_items = re.findall(
        r"(?:^|\s)\d+[.)]\s*([\s\S]*?)(?=(?:\s+\d+[.)]\s)|$)",
        text,
    )
    if len(numbered_items) >= 2:
        cleaned = [item.strip().rstrip(".!?") for item in numbered_items if item.strip()]
        if cleaned:
            return ". ".join(cleaned) + "."

    return text

'''
def build_prompt(preferences: dict[str, Any]) -> str:
    return f"""
You are a professional nutritionist and chef. Generate a 4-week meal plan.

User preferences:
- Monthly budget: ${preferences.get("monthlyBudget")}
- Goal: {preferences.get("goalType")}
- Dietary tags: {preferences.get("dietaryTags", [])}
- Allergies (strictly exclude): {preferences.get("allergies", [])}

Rules:
- Produce exactly 28 meals total.
- Ensure the price for the meal is accurate based on sum of current prices of each ingredient in Northwest Oregon
- Make sure the meal total is the sum of all of the ingredient costs.
- Ensure the meal plan stays within 60-70% of the users monthly budget to allow for breakfast, lunch, and snacks.
- Ensure the prep time accurately reflects the time it would take to prepare the meal based on the included ingredients and instructions.
- Every meal MUST be a dinner meal.
- Set `mealType` to exactly "Dinner" for every meal.
- Strictly exclude allergens listed above.
- Keep meals diverse across the month.
- Include practical ingredient measurements.
- Every `ingredientItems[*].ingredientId` MUST exactly match an existing key in `ingredientPrices`.
- Do not invent, rename, singularize, or pluralize ingredient IDs between sections.
- `instructions` must be one plain string of sentence steps separated by period+space.
- Do not include numbering (e.g. `1.`), bullets, markdown, or newline separators in `instructions`.
- Return only raw JSON with no markdown.

Return JSON with this exact top-level shape:
{{
  "mealPlan": [
    {{
      "name": "meal name",
      "calories": 500,
      "carbs": 60,
      "fat": 15,
      "protein": 30,
      "prepTime": "10 minutes",
      "cookTime": "20 minutes",
      "servings": 2,
      "costPerServing": 2.5,
      "mealType": "Dinner",
      "difficulty": "Easy",
      "instructions": "Heat oil in a pan. Add ingredients and cook through. Season and serve warm.",
      "tags": ["budget-friendly"],
      "tips": "Optional helpful tip",
      "source": "generated",
      "ingredientItems": [
        {{
          "ingredientId": "ingredient_oats_grains",
          "originalText": "1 cup rolled oats",
          "quantity": 1,
          "unit": "cup",
          "notes": ""
        }}
      ],
      "ingredients": ["1 Cup Rolled Oats"]
    }}
  ],
  "ingredientPrices": {{
    "ingredient_oats_grains": {{
      "name": "rolled oats",
      "category": "grains",
      "defaultUnit": "cup",
      "snapEligible": true,
      "aliases": ["oats"],
      "price": {{
        "value": 0.3,
        "currency": "USD",
        "unitQuantity": 1,
        "unit": "cup"
      }}
    }}
  }}
}}
"""
'''
#The above prompt is the original combined prompt. The following prompts are the new split prompts for a two-pass approach.

def build_name_plan_prompt(preferences: dict[str, Any]) -> str:
    return f"""
You are a professional nutritionist and chef. Generate a 4-week meal plan outline.

User preferences:
- Monthly budget: ${preferences.get("monthlyBudget")}
- Goal: {preferences.get("goalType")}
- Dietary tags: {preferences.get("dietaryTags", [])}
- Allergies (strictly exclude): {preferences.get("allergies", [])}

Rules:
- Produce exactly 28 meals total (7 meals per week x 4 weeks).
- Use days in sequence: Monday to Sunday, then repeat for each week.
- For each meal include only: name, mealType, day, description.
- Set `mealType` to exactly "Dinner" for every meal.
- Keep description to one short sentence.
- Strictly exclude allergens listed above.
- Make sure each meal in unique so that the meal plan is diverse across the month.
- Return only raw JSON with no markdown.

Return JSON with this exact top-level shape:
{{
  "mealPlan": [
    {{
      "name": "meal name",
      "mealType": "Dinner",
      "day": "Monday",
      "description": "Short summary."
    }}
  ]
}}
"""


def build_meal_detail_prompt(preferences: dict[str, Any], meal_outline: MealOutline, ingredients_data: dict) -> str:
    ingredients_json_str = json.dumps(ingredients_data, indent=2)
    return f"""
You are a professional nutritionist and chef generating structured meal data as JSON.

## User Preferences
- Monthly budget: ${preferences.get("monthlyBudget")} USD/month
- Goal: {preferences.get("goalType")}
- Allergies — STRICTLY FORBIDDEN, never include: {preferences.get("allergies", [])}

## Target Meal
- Name: {meal_outline.name}
- Type: {meal_outline.mealType}
- Day: {meal_outline.day}
- Description: {getattr(meal_outline, "description", "")}

## Ingredient Price Reference
The JSON below lists EVERY ingredient you may use. Each entry has a price per unit.
RULES — read carefully:
1. Every ingredientId you use MUST be an exact key from this object. Copy it character-for-character.
2. Do NOT invent, rename, pluralize, or abbreviate ingredient IDs.
3. Use the EXACT unit listed for each ingredient in your ingredientItems (e.g. if the unit is "tbsp", your quantity must be in tbsp).
4. If you want an ingredient not listed here, omit it or substitute the closest listed one.

{ingredients_json_str}

## Cost Calculation — do this math yourself before writing costPerServing
  For each ingredient: item_cost = price * quantity  (units already match — no conversion needed)
  total_cost = sum of all item_costs
  costPerServing = round(total_cost / servings, 2)

## Other Rules
- mealType MUST be exactly "Dinner"
- prepTime and cookTime must be realistic (e.g. "15 minutes", "25 minutes")
- instructions: one plain string, steps separated by ". " — NO numbering, NO bullets, NO newlines
- Strictly exclude all allergens listed above
- Return ONLY raw JSON — no markdown fences, no explanation

## Required JSON Shape
{{
  "meal": {{
    "name": "{meal_outline.name}",
    "calories": 550,
    "carbs": 45,
    "fat": 18,
    "protein": 38,
    "prepTime": "15 minutes",
    "cookTime": "25 minutes",
    "servings": 4,
    "costPerServing": 3.75,
    "mealType": "Dinner",
    "difficulty": "Medium",
    "instructions": "Heat oil over medium heat. Add garlic and cook 1 minute. Add protein and cook through. Season and serve.",
    "tags": ["high-protein", "budget-friendly"],
    "tips": "Optional tip here",
    "source": "generated",
    "ingredientItems": [
      {{
        "ingredientId": "chicken_breast_boneless",
        "originalText": "1.5 lbs boneless chicken breast",
        "quantity": 1.5,
        "unit": "lb",
        "notes": "cubed"
      }}
    ],
    "ingredients": ["1.5 lbs boneless chicken breast, cubed"]
  }},
  "ingredientPrices": {{
    "chicken_breast_boneless": {{
      "name": "boneless chicken breast",
      "category": "protein",
      "defaultUnit": "lb",
      "snapEligible": true,
      "aliases": ["chicken breast"],
      "price": {{
        "value": 3.49,
        "currency": "USD",
        "unitQuantity": 1,
        "unit": "lb"
      }}
    }}
  }}
}}
"""

def load_ingredient_list() -> dict[str, Any]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "..", "accurate_ingredients.json")
    with open(path, "r") as f:
        return json.load(f)
    
def _flatten_ingredients(nested: dict) -> dict:
    """Converts category-nested ingredient JSON into a flat id->data dict."""
    flat = {}
    for category, items in nested.items():
        for key, data in items.items():
            flat[key] = data
    return flat


# Common suffixes Gemini adds or drops relative to our canonical IDs.
_STRIP_SUFFIXES = [
    "_boneless", "_fillet", "_fresh", "_whole", "_sliced",
    "_frozen_peeled", "_peeled", "_ground", "_canned",
    "_shredded", "_unsalted", "_evoo", "_plain",
]

# Explicit alias table for the most common mismatches.
# Add entries here whenever [WARN] logs show a recurring unmatched ID.
_ID_ALIAS_TABLE: dict[str, str] = {
    # Poultry
    "chicken_breast":           "chicken_breast_boneless",
    "chicken_thigh":            "chicken_thighs_boneless",
    "chicken_thighs":           "chicken_thighs_boneless",
    "chicken_thigh_boneless":   "chicken_thighs_boneless",
    "chicken_thigh_bone_in":    "chicken_thighs_bonein",
    "chicken_drumstick":        "chicken_drumsticks",
    # Beef
    "ground_beef":              "beef_ground_90_10",
    "beef_ground":              "beef_ground_90_10",
    "sirloin_steak":            "beef_sirloin_steak",
    "beef_sirloin":             "beef_sirloin_steak",
    "chuck_roast":              "beef_chuck_roast",
    # Pork
    "pork_chop":                "pork_chops_boneless",
    "pork_chops":               "pork_chops_boneless",
    # Fish
    "tilapia":                  "tilapia_fillet",
    "salmon":                   "salmon_fillet",
    "cod":                      "cod_fillet",
    "shrimp":                   "shrimp_frozen_peeled",
    # Vegetables
    "garlic":                   "garlic_clove",
    "garlic_minced":            "garlic_clove",
    "garlic_cloves":            "garlic_clove",
    "onion":                    "onion_yellow",
    "spinach":                  "spinach_fresh",
    "bell_pepper":              "bell_pepper_red",
    "sweet_potato":             "potato_sweet",
    "russet_potato":            "potato_russet",
    # Dairy
    "butter":                   "butter_unsalted",
    "parmesan":                 "cheese_parmesan",
    "cheddar":                  "cheese_cheddar_shredded",
    "greek_yogurt":             "yogurt_greek_plain",
    # Pantry
    "olive_oil":                "olive_oil_evoo",
    "extra_virgin_olive_oil":   "olive_oil_evoo",
    "black_beans":              "black_beans_canned",
    "kidney_beans":             "kidney_beans_canned",
    "diced_tomatoes":           "diced_tomatoes_canned",
    "crushed_tomatoes_canned":  "crushed_tomatoes",
    "tomato_sauce":             "tomato_sauce_canned",
    "chickpeas":                "chickpeas_canned",
    "refried_beans":            "refried_beans_canned",
    "coconut_milk":             "coconut_milk_canned",
    # Dairy extras
    "heavy_cream":              "cream_heavy",
    "heavy_cream_cup":          "cream_heavy",
    "mozzarella":               "cheese_mozzarella",
    "mozzarella_cheese":        "cheese_mozzarella",
    "feta_cheese":              "cheese_feta",
    "ricotta_cheese":           "cheese_ricotta",
    # Produce extras
    "mushrooms":                "mushrooms_cremini",
    "cremini_mushrooms":        "mushrooms_cremini",
    "white_mushrooms":          "mushrooms_white",
    "peas":                     "peas_frozen",
    "frozen_peas":              "peas_frozen",
    "green_beans":              "green_beans_fresh",
    # Grains extras
    "arborio_rice":             "rice_arborio",
    "linguine":                 "pasta_linguine",
    "fettuccine":               "pasta_fettuccine",
    "red_lentils":              "lentils_red",
    "green_lentils":            "lentils_green",
    # Spices
    "italian_seasoning_tsp":    "italian_seasoning",
    "cumin":                    "cumin_ground",
}


def _resolve_ingredient_id(ingredient_id: str, all_ingredients: dict) -> Optional[str]:
    """
    Match a Gemini-returned ID to a real key in all_ingredients.
    Resolution order (most to least precise):
      1. Exact match
      2. Explicit alias table  
      3. Strip common suffixes then exact/prefix match
      4. First-two-segment prefix match (e.g. beef_ground -> beef_ground_90_10)
    Deliberately avoids loose substring matching which caused wrong-ingredient matches.
    """
    if ingredient_id in all_ingredients:
        return ingredient_id

    # 1. Explicit alias table — handles the most common Gemini variants precisely
    alias = _ID_ALIAS_TABLE.get(ingredient_id)
    if alias and alias in all_ingredients:
        return alias

    # 2. Strip common suffixes then try exact + prefix match
    normalized = ingredient_id
    for suffix in _STRIP_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break

    if normalized in all_ingredients:
        return normalized

    for key in all_ingredients:
        if key.startswith(normalized + "_"):
            return key

    # 3. Reverse: Gemini gave something longer, our key is a prefix of it
    for key in all_ingredients:
        if ingredient_id.startswith(key + "_"):
            return key

    # 4. First two segments only (e.g. beef_ground_lean -> beef_ground_90_10)
    parts = ingredient_id.split("_")
    if len(parts) >= 2:
        two_seg = "_".join(parts[:2])
        for key in all_ingredients:
            if key.startswith(two_seg + "_") or key == two_seg:
                return key

    return None

def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        chunks = text.split("```")
        for chunk in chunks:
            candidate = chunk.strip()
            if not candidate:
                continue
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{"):
                return candidate
    return text


def _generate_raw_response(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables")

    # Preferred SDK path (google-genai).
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        if not getattr(response, "text", None):
            raise ValueError("Gemini returned an empty response body")
        return response.text
    except Exception as primary_exc:
        # Compatibility fallback for environments that only have google-generativeai.
        try:
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=api_key)
            model = legacy_genai.GenerativeModel(
                GEMINI_MODEL,
                generation_config={"response_mime_type": "application/json", "temperature": 0.2},
            )
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            if not text:
                raise ValueError("Gemini returned an empty response body")
            return text
        except Exception as fallback_exc:
            raise ValueError(
                "Failed to initialize Gemini SDK. Install `google-genai` or "
                "`google-generativeai`. "
                f"primary={primary_exc}; fallback={fallback_exc}"
            ) from fallback_exc


def _call_and_parse(
    prompt: str,
    parser: type[TModel],
    retries: int = DEFAULT_RETRIES,
    timeout_seconds: int = GEMINI_CALL_TIMEOUT_SECONDS,
) -> TModel:
    """
    Call Gemini with retries and exponential-ish backoff.
    Passes timeout_seconds through so name-pass and detail-pass can use different limits.
    Backs off after each failure so rate-limited requests have time to recover.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            raw_text = _run_with_timeout(
                _generate_raw_response,
                prompt,
                timeout_seconds=timeout_seconds,
            )
            json_text = _extract_json_text(raw_text)
            payload = json.loads(json_text)
            return parser(**payload)
        except Exception as exc:
            last_error = exc
            is_last = attempt == retries
            print(f"Gemini attempt {attempt}/{retries} failed: {exc}")
            if not is_last:
                # Back off before retrying: base delay + attempt multiplier.
                backoff = GEMINI_RETRY_BACKOFF_SECONDS * attempt
                print(f"Gemini backing off {backoff:.1f}s before retry {attempt + 1}/{retries}")
                import time as _time
                _time.sleep(backoff)

    raise ValueError(f"Gemini failed after {retries} attempts: {last_error}")

'''
def call_gemini(prompt: str, retries: int = DEFAULT_RETRIES) -> GeminiResponse:
    response = _call_and_parse(prompt, GeminiResponse, retries=retries)
    for meal in response.mealPlan:
        actual_total_cost = 0
        for item in meal.ingredientItems:
            # Look up the REAL price from your JSON file
            master_data = INGREDIENT_MASTER.get(item.ingredientId)
            if master_data:
                # Calculate the math in Python (Accurate!)
                item_cost = master_data['price'] * item.quantity
                actual_total_cost += item_cost
        
        # Overwrite the AI's potentially wrong math
        meal.costPerServing = round(actual_total_cost / meal.servings, 2)
        
    return response

def generate_meal_plan(preferences: dict[str, Any], retries: int = DEFAULT_RETRIES) -> GeminiResponse:
    prompt = build_prompt(preferences)
    return call_gemini(prompt, retries=retries)
'''

def generate_meal_name_plan(preferences: dict[str, Any], retries: int = DEFAULT_RETRIES) -> MealNamePlanResponse:
    prompt = build_name_plan_prompt(preferences)
    # Name pass is lightweight (names + days only) so use the shorter timeout.
    response = _call_and_parse(prompt, MealNamePlanResponse, retries=retries, timeout_seconds=GEMINI_NAME_PASS_TIMEOUT_SECONDS)
    if len(response.mealPlan) != 28:
        raise ValueError(f"Expected 28 meals in name pass, got {len(response.mealPlan)}")
    for meal in response.mealPlan:
        meal.mealType = "Dinner"
    return response


def generate_meal_details(
    preferences: dict[str, Any],
    meal_outline: MealOutline,
    retries: int = DEFAULT_RETRIES,
) -> MealDetailResponse:
    meal_outline.mealType = "Dinner"
    raw_ingredients = load_ingredient_list()
    all_ingredients = _flatten_ingredients(raw_ingredients)

    # Pass only the relevant subset — keeps prompt small so Gemini uses correct IDs
    relevant_ingredients = _select_relevant_ingredients(
        meal_outline.name,
        getattr(meal_outline, "description", ""),
        all_ingredients,
    )

    prompt = build_meal_detail_prompt(preferences, meal_outline, relevant_ingredients)
    response = _call_and_parse(prompt, MealDetailResponse, retries=retries)
    response.meal.mealType = "Dinner"
    response.meal.instructions = _normalize_instruction_text(response.meal.instructions)

    # Recalculate costPerServing in Python — overrides any hallucinated math from Gemini.
    # Uses fuzzy ID resolution to handle Gemini dropping/adding suffixes like _boneless, _fresh.
    actual_total_cost = 0.0
    unmatched: list[str] = []

    for item in response.meal.ingredientItems:
        resolved_id = _resolve_ingredient_id(item.ingredientId, all_ingredients)
        if resolved_id:
            if resolved_id != item.ingredientId:
                print(f"[INFO] Resolved '{item.ingredientId}' -> '{resolved_id}' for '{meal_outline.name}'")
            master = all_ingredients[resolved_id]
            actual_total_cost += master["price"] * item.quantity
        else:
            # Last resort: use Gemini's returned price
            ai_price = response.ingredientPrices.get(item.ingredientId)
            if ai_price:
                actual_total_cost += ai_price.price.value * item.quantity
            unmatched.append(item.ingredientId)

    if unmatched:
        print(f"[WARN] Truly unmatched IDs for '{meal_outline.name}' (add to JSON or KEYWORD_MAP): {unmatched}")

    if response.meal.servings > 0 and actual_total_cost > 0:
        response.meal.costPerServing = round(actual_total_cost / response.meal.servings, 2)

    return response
