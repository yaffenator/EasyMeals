#!/usr/bin/env python3
"""
seed_firestore.py

Seeds Firestore with:
- meta/globalStats                                 (global rating stats for Bayesian scoring)
- ingredients/{ingredientId}                       (canonical ingredient docs; NO measurements in names/ids)
- recipes/{recipeId}                               (DetailedRecipe + ingredientItems w/ optional quantity/unit)
- users/{uid}
- users/{uid}/plans/{planId}                       (standardized to 'plans' not 'mealPlans')

Service account setup:
1) Put `serviceAccountKey.json` in `backend/secrets/`, OR
2) Set FIREBASE_SERVICE_ACCOUNT to the full JSON credential string.

Run:
  python seed_firestore.py

Optional:
  python seed_firestore.py --project YOUR_PROJECT_ID
  python seed_firestore.py --user-id SOME_UID
  python seed_firestore.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import firebase_admin
from firebase_admin import credentials, firestore


# -----------------------------
# Firebase init
# -----------------------------

def init_firestore(project_id: Optional[str] = None) -> firestore.Client:
    if firebase_admin._apps:
        return firestore.client()

    firebase_env_creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    script_dir = Path(__file__).resolve().parent
    local_candidates = [
        script_dir / "secrets" / "serviceAccountKey.json",
        script_dir / "serviceAccountKey.json",
    ]

    if firebase_env_creds:
        try:
            cred_obj = credentials.Certificate(json.loads(firebase_env_creds))
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT is set, but it is not valid JSON.") from exc
    else:
        local_key_path = next((p for p in local_candidates if p.exists()), None)
        if local_key_path:
            cred_obj = credentials.Certificate(str(local_key_path))
        else:
            raise FileNotFoundError(
                "No service account key found. Set FIREBASE_SERVICE_ACCOUNT or place "
                "serviceAccountKey.json in backend/secrets/."
            )

    options: Dict[str, Any] = {}
    if project_id:
        options["projectId"] = project_id

    firebase_admin.initialize_app(cred_obj, options=options or None)
    return firestore.client()


# -----------------------------
# Helpers
# -----------------------------

def now_ts() -> datetime:
    return datetime.now(timezone.utc)

def round2(x: float) -> float:
    return float(f"{x:.2f}")

def estimate_macros_from_calories(calories: int) -> Dict[str, int]:
    protein = round(calories * 0.25 / 4)
    carbs = round(calories * 0.45 / 4)
    fat = round(calories * 0.30 / 9)
    return {"protein": int(protein), "carbs": int(carbs), "fat": int(fat)}

def difficulty_from_prep(prep_minutes: int) -> str:
    if prep_minutes > 35:
        return "Hard"
    if prep_minutes > 25:
        return "Medium"
    return "Easy"

def cook_time_from_prep(prep_minutes: int) -> int:
    return int(prep_minutes + round(prep_minutes * 0.5))

def cost_per_serving(total_cost: float, servings: int) -> float:
    if servings <= 0:
        return round2(total_cost)
    return round2(total_cost / servings)


# -----------------------------
# Ingredient canonicalization (NO measurements in ingredient doc IDs/names)
# -----------------------------

UNITS = r"(?:oz|ounce|ounces|lb|lbs|pound|pounds|g|gram|grams|kg|cup|cups|tbsp|tablespoon|tablespoons|tsp|teaspoon|teaspoons|clove|cloves|can|cans|fillet|fillets|each)"
FRACTION = r"(?:\d+\s*/\s*\d+)"
NUMBER = r"(?:\d+(?:\.\d+)?)"
MIXED = rf"(?:{NUMBER}\s+{FRACTION})"
RANGE = rf"(?:{NUMBER}\s*-\s*{NUMBER})"
QTY_TOKEN = rf"(?:{MIXED}|{FRACTION}|{RANGE}|{NUMBER})"

LEADING_QTY_UNIT_RE = re.compile(
    rf"^\s*(?P<qty>{QTY_TOKEN})\s*(?P<unit>{UNITS})?\b\s*(?P<rest>.*)$",
    re.IGNORECASE,
)

PAREN_RE = re.compile(r"\([^)]*\)")
EXTRA_SPACE_RE = re.compile(r"\s+")
FILLER_RE = re.compile(r"\b(to taste|for garnish)\b", re.IGNORECASE)

def _norm_unit(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.lower()
    mapping = {
        "ounce": "oz", "ounces": "oz",
        "pound": "lb", "pounds": "lb", "lbs": "lb",
        "gram": "g", "grams": "g",
        "tablespoon": "tbsp", "tablespoons": "tbsp",
        "teaspoon": "tsp", "teaspoons": "tsp",
        "cloves": "clove",
        "cans": "can",
        "fillets": "fillet",
    }
    return mapping.get(u, u)

def _try_parse_qty(q: str) -> Optional[float]:
    q = q.strip()
    if " " in q and "/" in q:
        left, frac = q.split(None, 1)
        try:
            whole = float(left)
            num, den = frac.split("/", 1)
            return whole + (float(num) / float(den))
        except Exception:
            return None
    if "/" in q:
        try:
            num, den = q.split("/", 1)
            return float(num) / float(den)
        except Exception:
            return None
    if "-" in q:
        try:
            a, _b = q.split("-", 1)
            return float(a.strip())
        except Exception:
            return None
    try:
        return float(q)
    except Exception:
        return None

def canonicalize_ingredient_name(original_line: str) -> str:
    """
    Returns a canonical ingredient name with:
    - NO leading measurements (qty/unit)
    - NO parenthetical package notes
    - NO "to taste" / "for garnish"
    - No comma-notes (e.g., diced/minced) included in the name
    """
    line = original_line.strip()
    base = line.split(",", 1)[0].strip()
    base = PAREN_RE.sub("", base).strip()
    base = FILLER_RE.sub("", base).strip()
    m = LEADING_QTY_UNIT_RE.match(base)
    if m:
        rest = (m.group("rest") or "").strip()
        base = rest if rest else base
    base = EXTRA_SPACE_RE.sub(" ", base).strip()
    return base or original_line.strip()

def parse_ingredient_line(line: str) -> Tuple[Optional[float], Optional[str], str, Optional[str]]:
    """
    Parses a line into:
    - qty (optional float)
    - unit (optional normalized string)
    - canonical_name (NO measurements)
    - notes (optional string after comma)
    """
    original = line.strip()

    notes = None
    if "," in original:
        left, right = original.split(",", 1)
        base_part = left.strip()
        notes = right.strip() or None
    else:
        base_part = original

    qty = None
    unit = None

    base_no_paren = PAREN_RE.sub("", base_part).strip()
    m = LEADING_QTY_UNIT_RE.match(base_no_paren)
    if m:
        qty = _try_parse_qty(m.group("qty") or "")
        unit = _norm_unit(m.group("unit"))

    canonical_name = canonicalize_ingredient_name(original)
    return qty, unit, canonical_name, notes

def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or uuid.uuid4().hex


# -----------------------------
# Generator-style recipe content
# -----------------------------

def generate_ingredients(meal_name: str) -> List[str]:
    # Fixed: was using toLower() (JavaScript) — now using .lower() (Python)
    lower = meal_name.lower()

    if "chicken" in lower and "pasta" in lower:
        return [
            "12 oz pasta (penne or linguine)",
            "1 lb chicken breast, diced",
            "2 cups cream or milk",
            "1 cup parmesan cheese, grated",
            "3 cloves garlic, minced",
            "2 tbsp olive oil",
            "1 cup spinach or vegetables",
            "Salt and pepper to taste",
            "Fresh herbs for garnish",
        ]

    if "salmon" in lower:
        return [
            "4 salmon fillets (6 oz each)",
            "2 cups broccoli florets",
            "2 bell peppers, sliced",
            "1 zucchini, sliced",
            "3 tbsp olive oil",
            "2 cloves garlic, minced",
            "Lemon juice and zest",
            "Fresh herbs (dill or parsley)",
            "Salt and pepper to taste",
        ]

    if "beef" in lower and ("stir" in lower or "bowl" in lower):
        return [
            "1 lb beef sirloin, thinly sliced",
            "3 cups cooked rice",
            "2 cups mixed vegetables",
            "3 tbsp soy sauce",
            "2 tbsp oyster or teriyaki sauce",
            "1 tbsp sesame oil",
            "2 cloves garlic, minced",
            "1 tbsp ginger, grated",
            "2 tbsp vegetable oil",
            "Green onions and sesame seeds for garnish",
        ]

    if "bowl" in lower or "burrito" in lower:
        return [
            "2 cups cooked rice or quinoa",
            "1 can (15 oz) black beans, drained",
            "1 cup corn kernels",
            "1 bell pepper, diced",
            "1 avocado, sliced",
            "1 cup cherry tomatoes, halved",
            "1/2 cup shredded cheese",
            "Lime juice",
            "Fresh cilantro",
            "Sour cream or Greek yogurt",
            "Salt, pepper, and cumin to taste",
        ]

    if "meatball" in lower:
        return [
            "1 lb ground turkey or beef",
            "1/2 cup breadcrumbs",
            "1 egg",
            "1/4 cup parmesan cheese",
            "2 cloves garlic, minced",
            "2 cups marinara or BBQ sauce",
            "1 tbsp Italian seasoning",
            "Salt and pepper to taste",
            "Fresh basil for garnish",
            "Cooked pasta or rice for serving",
        ]

    if "taco" in lower:
        return [
            "1 lb shrimp, peeled and deveined",
            "8 small tortillas",
            "2 cups shredded cabbage",
            "1 cup cherry tomatoes, diced",
            "1 avocado, sliced",
            "1/4 cup sour cream or mayo",
            "Lime juice",
            "2 tsp chili powder",
            "Fresh cilantro",
            "Salt and pepper to taste",
        ]

    if "curry" in lower:
        return [
            "1 lb chicken, cubed",
            "1 can (14 oz) coconut milk",
            "2 tbsp curry paste or powder",
            "1 onion, diced",
            "2 cloves garlic, minced",
            "1 tbsp ginger, grated",
            "2 cups vegetables (bell peppers, carrots)",
            "3 cups cooked basmati rice",
            "2 tbsp oil",
            "Fresh cilantro",
            "Salt to taste",
        ]

    return [
        "Main protein (1 lb)",
        "Vegetables (2-3 cups)",
        "Aromatics (garlic, onion)",
        "Oil or butter (2-3 tbsp)",
        "Seasonings and spices",
        "Fresh herbs",
        "Salt and pepper to taste",
    ]


def generate_instructions(meal_name: str) -> List[str]:
    lower = meal_name.lower()

    if "pasta" in lower:
        return [
            "Cook pasta according to package directions. Drain and set aside.",
            "Heat oil in a large skillet over medium-high heat. Season protein with salt and pepper.",
            "Cook protein until golden brown and cooked through, about 6-8 minutes. Remove from skillet.",
            "In the same skillet, add aromatics and cook until fragrant, about 1 minute.",
            "Add cream or sauce and bring to a simmer. Cook for 3-4 minutes until slightly thickened.",
            "Stir in cheese until melted and smooth.",
            "Add any vegetables and cook until wilted or tender.",
            "Return protein to the skillet along with cooked pasta. Toss to combine.",
            "Season with additional salt and pepper if needed.",
            "Garnish with fresh herbs and serve hot.",
        ]

    if "salmon" in lower or "fish" in lower:
        return [
            "Preheat oven to 425°F (220°C).",
            "Toss vegetables with oil, salt, and pepper. Spread on a baking sheet.",
            "Roast vegetables for 15 minutes.",
            "Meanwhile, season fish with salt, pepper, and aromatics.",
            "Heat oil in an oven-safe skillet over medium-high heat.",
            "Sear fish for 3-4 minutes until golden on one side.",
            "Flip fish and transfer skillet to oven with the vegetables.",
            "Bake for 8-10 minutes until fish is cooked through and flakes easily.",
            "Squeeze fresh citrus juice over fish and garnish with herbs.",
            "Serve immediately with roasted vegetables.",
        ]

    if "stir fry" in lower or ("beef" in lower and "bowl" in lower):
        return [
            "Prepare rice according to package directions if not already cooked.",
            "Mix sauce ingredients in a small bowl and set aside.",
            "Heat oil in a large wok or skillet over high heat.",
            "Add protein in a single layer and cook without stirring for 2 minutes.",
            "Stir and continue cooking until browned. Remove and set aside.",
            "Add vegetables and stir-fry for 3-4 minutes until crisp-tender.",
            "Add aromatics and cook for 30 seconds until fragrant.",
            "Return protein to the wok and pour in the sauce.",
            "Toss everything together for 1-2 minutes until well coated.",
            "Serve over rice with garnishes.",
        ]

    if "bowl" in lower or "burrito" in lower:
        return [
            "Cook rice or grains according to package directions.",
            "Heat beans in a small pot with seasonings until warm.",
            "Prepare all vegetables by dicing, slicing, or chopping as needed.",
            "If using, cook any protein with oil and seasonings until done.",
            "Divide rice among serving bowls.",
            "Top each bowl with beans, vegetables, and protein.",
            "Add fresh toppings like avocado, cheese, and herbs.",
            "Drizzle with dressing or add sour cream.",
            "Squeeze fresh lime juice over each bowl.",
            "Serve immediately and enjoy!",
        ]

    if "meatball" in lower:
        return [
            "Preheat oven to 400°F (200°C) and line a baking sheet with parchment paper.",
            "In a large bowl, combine ground meat, breadcrumbs, egg, cheese, and seasonings.",
            "Mix gently until just combined - don't overmix.",
            "Form mixture into 1.5-inch meatballs and place on prepared baking sheet.",
            "Bake for 15-20 minutes until cooked through and browned.",
            "While meatballs bake, heat sauce in a large skillet.",
            "Add cooked meatballs to the sauce and simmer for 5-10 minutes.",
            "Cook pasta or rice according to package directions.",
            "Serve meatballs and sauce over pasta or rice.",
            "Garnish with fresh herbs and grated cheese.",
        ]

    if "taco" in lower:
        return [
            "Season protein with spices, salt, and pepper.",
            "Heat oil in a skillet over medium-high heat.",
            "Cook protein until done (4-5 minutes for shrimp, 6-8 for chicken).",
            "Warm tortillas in a dry skillet or microwave.",
            "Prepare slaw by mixing cabbage with lime juice and a pinch of salt.",
            "Mix sour cream or mayo with lime juice for crema.",
            "Assemble tacos by layering tortillas with protein.",
            "Top with slaw, tomatoes, and avocado.",
            "Drizzle with crema and garnish with cilantro.",
            "Serve immediately with lime wedges.",
        ]

    if "curry" in lower:
        return [
            "Cook rice according to package directions.",
            "Heat oil in a large pot or deep skillet over medium heat.",
            "Add onion and cook until softened, about 5 minutes.",
            "Add garlic and ginger, cook for 1 minute until fragrant.",
            "Stir in curry paste or powder and cook for 30 seconds.",
            "Add protein and cook until browned on all sides.",
            "Pour in coconut milk and bring to a simmer.",
            "Add vegetables and simmer for 10-15 minutes until tender.",
            "Season with salt and adjust spices to taste.",
            "Serve over rice, garnished with fresh cilantro.",
        ]

    return [
        "Prepare all ingredients by washing, chopping, and measuring.",
        "Heat oil in a large pan over medium-high heat.",
        "Cook protein until browned and cooked through.",
        "Add aromatics and cook until fragrant.",
        "Add vegetables and other ingredients.",
        "Cook until everything is tender and well combined.",
        "Season to taste with salt and pepper.",
        "Garnish with fresh herbs.",
        "Serve hot and enjoy!",
    ]


def generate_tips(meal_name: str) -> List[str]:
    lower = meal_name.lower()

    if "pasta" in lower:
        return [
            "Save some pasta water to thin the sauce if needed",
            "Don't rinse pasta after cooking - the starch helps sauce adhere",
            "Leftovers keep well in the fridge for up to 3 days",
        ]

    if "salmon" in lower or "fish" in lower:
        return [
            "Check fish doneness by gently pressing - it should flake easily",
            "Don't overcook! Fish continues cooking after removing from heat",
            "Serve with a squeeze of fresh lemon for brightness",
        ]

    if "stir fry" in lower or "beef" in lower:
        return [
            "Slice meat against the grain for maximum tenderness",
            "Have all ingredients prepped before starting - this cooks fast!",
            "Use day-old rice for the best texture and to prevent mushiness",
        ]

    if "bowl" in lower:
        return [
            "Meal prep by preparing components separately and storing in containers",
            "Customize with your favorite toppings and sauces",
            "Make it vegan by omitting dairy and using plant-based protein",
        ]

    if "meatball" in lower:
        return [
            "Don't overmix the meat mixture or meatballs will be tough",
            "Wet your hands when rolling meatballs to prevent sticking",
            "These freeze beautifully - make a double batch!",
        ]

    if "taco" in lower:
        return [
            "Warm tortillas for better flavor and flexibility",
            "Prep toppings in advance for quick assembly",
            "Use any protein you like - fish, chicken, or beans work great",
        ]

    if "curry" in lower:
        return [
            "Adjust curry paste amount based on your spice preference",
            "Add vegetables that take longer to cook first",
            "Tastes even better the next day as flavors meld together",
        ]

    return [
        "Taste and adjust seasonings before serving",
        "Leftovers can be stored in the fridge for 3-4 days",
        "Feel free to substitute ingredients based on what you have",
    ]


# -----------------------------
# Seed data
# -----------------------------

@dataclass(frozen=True)
class BaseRecipeSeed:
    name: str
    calories: int
    prep_minutes: int
    servings: int
    total_cost: float
    meal_type: str


BASE_RECIPES: List[BaseRecipeSeed] = [
    BaseRecipeSeed(name="Chicken Alfredo Pasta", calories=650, prep_minutes=25, servings=4, total_cost=16.00, meal_type="dinner"),
    BaseRecipeSeed(name="Salmon & Roasted Veggies", calories=520, prep_minutes=20, servings=2, total_cost=14.50, meal_type="dinner"),
    BaseRecipeSeed(name="Beef Stir Fry Bowl", calories=700, prep_minutes=30, servings=4, total_cost=18.75, meal_type="lunch"),
    BaseRecipeSeed(name="Veggie Burrito Bowl", calories=600, prep_minutes=15, servings=4, total_cost=12.00, meal_type="lunch"),
    BaseRecipeSeed(name="Turkey Meatballs & Marinara", calories=680, prep_minutes=40, servings=4, total_cost=17.25, meal_type="dinner"),
    BaseRecipeSeed(name="Shrimp Tacos", calories=540, prep_minutes=20, servings=4, total_cost=15.00, meal_type="dinner"),
    BaseRecipeSeed(name="Coconut Chicken Curry", calories=720, prep_minutes=35, servings=4, total_cost=16.50, meal_type="dinner"),
]


# -----------------------------
# Builders
# -----------------------------

def build_ingredient_doc(canonical_name: str) -> Dict[str, Any]:
    """
    Builds an ingredient document matching the nested price map structure
    that ingredient_service.py reads and writes.
    """
    return {
        "name": canonical_name,
        "aliases": [],
        "category": "uncategorized",
        "defaultUnit": "piece",
        "snapEligible": True,
        # Nested price map — matches ingredient_service.py's get_or_create_ingredient
        "price": {
            "value": 1.0,
            "currency": "USD",
            "unitQuantity": 1,
            "unit": "piece",
        },
        "createdAt": now_ts(),
        "updatedAt": now_ts(),
    }


def build_detailed_recipe_doc(
    db: firestore.Client,
    base: BaseRecipeSeed,
    ingredient_id_by_name: Dict[str, str],
) -> Dict[str, Any]:
    macros = estimate_macros_from_calories(base.calories)
    difficulty = difficulty_from_prep(base.prep_minutes)
    cook_time = cook_time_from_prep(base.prep_minutes)
    cps = cost_per_serving(base.total_cost, base.servings)

    protein_str = f"{macros['protein']}g"
    carbs_str = f"{macros['carbs']}g"
    fat_str = f"{macros['fat']}g"

    ingredient_lines = generate_ingredients(base.name)
    ingredient_items: List[Dict[str, Any]] = []

    for line in ingredient_lines:
        qty, unit, canon_name, notes = parse_ingredient_line(line)
        ing_id = ingredient_id_by_name.get(canon_name)

        item: Dict[str, Any] = {
            "ingredientId": ing_id,
            "ingredientRef": db.collection("ingredients").document(ing_id) if ing_id else None,
            "originalText": line,
        }
        if qty is not None:
            item["quantity"] = qty
        if unit is not None:
            item["unit"] = unit
        if notes is not None:
            item["notes"] = notes

        ingredient_items.append(item)

    instructions = generate_instructions(base.name)
    tips = generate_tips(base.name)

    return {
        "name": base.name,
        "mealType": base.meal_type,
        "calories": int(base.calories),
        "prepTime": int(base.prep_minutes),
        "cookTime": int(cook_time),
        "servings": int(base.servings),
        "totalCost": round2(base.total_cost),
        "costPerServing": round2(cps),

        "protein": protein_str,
        "carbs": carbs_str,
        "fat": fat_str,
        "difficulty": difficulty,

        "ingredients": ingredient_lines,
        "ingredientItems": ingredient_items,
        "instructions": instructions,
        "tips": tips,

        "nutritionInfo": {
            "calories": str(base.calories),
            "protein": protein_str,
            "carbs": carbs_str,
            "fat": fat_str,
        },

        "tags": list({base.meal_type, *[t for t in base.name.lower().replace("&", " ").replace("-", " ").split() if len(t) > 2]}),
        "source": "generated",

        # Rating fields required by rating_service.py and diversity_service.py
        "ratingCount": 0,
        "ratingSum": 0.0,
        "ratingAvg": 0.0,
        "recommendationScore": 0.0,

        "createdAt": now_ts(),
        "updatedAt": now_ts(),
    }


def build_user_plan_doc(db: firestore.Client, recipe_ids: List[str]) -> Dict[str, Any]:
    start = now_ts()
    end = start + timedelta(days=28)

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    slots = ["breakfast", "lunch", "dinner"]

    meals_all: List[Dict[str, Any]] = []
    # Build a full 4-week / 28-meal sequence by cycling recipe IDs.
    for i in range(28):
        rid = recipe_ids[i % len(recipe_ids)]
        snap = db.collection("recipes").document(rid).get()
        if not snap.exists:
            continue
        r = snap.to_dict() or {}

        day = days[i % len(days)]
        slot = slots[(i // len(days)) % len(slots)]

        meals_all.append({
            "id": rid,
            "recipeRef": db.collection("recipes").document(rid),
            "name": r.get("name"),
            "calories": r.get("calories"),
            "prepTime": r.get("prepTime"),
            "servings": r.get("servings"),
            "costPerServing": r.get("costPerServing"),
            "day": day,
            "slot": slot,
        })

    return {
        "startDate": start,
        "endDate": end,
        "status": "ready",
        "weeks": [
            {"weekIndex": 0, "meals": meals_all[:7]},
            {"weekIndex": 1, "meals": meals_all[7:14]},
            {"weekIndex": 2, "meals": meals_all[14:21]},
            {"weekIndex": 3, "meals": meals_all[21:28]},
        ],
        "createdAt": now_ts(),
        "updatedAt": now_ts(),
    }


def build_plan_days(weeks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    days: List[Dict[str, Any]] = []
    day_index = 0
    for week in weeks:
        week_index = int(week.get("weekIndex", 0))
        for meal in week.get("meals", []):
            day_index += 1
            days.append(
                {
                    "dayIndex": day_index,
                    "weekIndex": week_index,
                    "mealId": meal.get("id"),
                    "name": meal.get("name"),
                    "mealType": meal.get("slot"),
                    "costPerServing": meal.get("costPerServing"),
                    "calories": meal.get("calories"),
                    "recipeRef": meal.get("recipeRef"),
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
            )
    return days


# -----------------------------
# Main seed function
# -----------------------------

def seed(db: firestore.Client, user_id: str, dry_run: bool = False) -> None:

    # -----------------------------
    # meta/globalStats
    # Required by rating_service.py to track global average rating
    # without scanning the entire recipes collection on every rating submission.
    # -----------------------------
    if dry_run:
        print("[DRY RUN] Would write meta/globalStats")
    else:
        db.collection("meta").document("globalStats").set({
            "totalRatingSum": 0.0,
            "totalRatingCount": 0,
            "globalAvg": 3.0,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        print("Wrote meta/globalStats")

    # -----------------------------
    # users/{uid}
    # -----------------------------
    user_ref = db.collection("users").document(user_id)

    if dry_run:
        print(f"[DRY RUN] Would upsert users/{user_id}")
    else:
        user_ref.set(
            {"updatedAt": now_ts(), "createdAt": firestore.SERVER_TIMESTAMP},
            merge=True,
        )
        print(f"Upserted users/{user_id}")

    # -----------------------------
    # ingredients/
    # Build canonical ingredient set across all recipes
    # -----------------------------
    canonical_to_id: Dict[str, str] = {}
    ingredient_docs: Dict[str, Dict[str, Any]] = {}

    for base in BASE_RECIPES:
        for line in generate_ingredients(base.name):
            canon = canonicalize_ingredient_name(line)
            if canon not in canonical_to_id:
                ing_id = f"ingredient_{slugify(canon)}_uncategorized"
                canonical_to_id[canon] = ing_id
                ingredient_docs[ing_id] = build_ingredient_doc(canon)

    if dry_run:
        print(f"[DRY RUN] Would write {len(ingredient_docs)} ingredient docs to ingredients/")
    else:
        for ing_id, doc in ingredient_docs.items():
            db.collection("ingredients").document(ing_id).set(doc)
        print(f"Wrote {len(ingredient_docs)} docs to ingredients/")

    # -----------------------------
    # recipes/
    # -----------------------------
    recipe_ids: List[str] = []
    for base in BASE_RECIPES:
        recipe_id = uuid.uuid4().hex
        doc = build_detailed_recipe_doc(db=db, base=base, ingredient_id_by_name=canonical_to_id)
        recipe_ids.append(recipe_id)

        if dry_run:
            print(f"[DRY RUN] Would write recipes/{recipe_id}: {doc['name']}")
        else:
            db.collection("recipes").document(recipe_id).set(doc)
            print(f"Wrote recipes/{recipe_id}: {doc['name']}")

    # -----------------------------
    # users/{uid}/plans/{planId}
    # Standardized to 'plans' (not 'mealPlans') to match plan_service.py
    # -----------------------------
    plan_id = uuid.uuid4().hex
    plan_ref = user_ref.collection("plans").document(plan_id)

    if dry_run:
        print(f"[DRY RUN] Would write users/{user_id}/plans/{plan_id} referencing {len(recipe_ids)} recipes")
    else:
        plan_doc = build_user_plan_doc(db=db, recipe_ids=recipe_ids)
        plan_ref.set(plan_doc)
        for day in build_plan_days(plan_doc.get("weeks", [])):
            day_id = f"day_{day['dayIndex']:02d}"
            plan_ref.collection("days").document(day_id).set(day)
        print(f"Wrote users/{user_id}/plans/{plan_id}")


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Firestore with ingredients + recipes + user plans subcollection."
    )
    parser.add_argument("--project", dest="project_id", default=None, help="Override Firebase project id (optional).")
    parser.add_argument("--user-id", dest="user_id", default="demo_user", help="User UID to own the seeded meal plan.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Print actions without writing to Firestore.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        db = init_firestore(project_id=args.project_id)
        seed(db, user_id=args.user_id, dry_run=args.dry_run)
        print("Done.")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
