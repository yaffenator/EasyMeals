import json
import os
from typing import Any, Optional

from pydantic import BaseModel, Field

GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_RETRIES = 3


class IngredientItem(BaseModel):
    ingredientId: str
    originalText: str
    quantity: float
    unit: str
    notes: str = ""


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


def build_prompt(preferences: dict[str, Any]) -> str:
    return f"""
You are a professional nutritionist and chef. Generate a 4-week meal plan.

User preferences:
- Monthly budget: ${preferences.get("monthlyBudget")}
- Goal: {preferences.get("goalType")}
- Dietary tags: {preferences.get("dietaryTags", [])}
- Allergies (strictly exclude): {preferences.get("allergies", [])}

Rules:
- Produce exactly 28 meals total across breakfast/lunch/dinner.
- Strictly exclude allergens listed above.
- Keep meals diverse across the month.
- Include practical ingredient measurements.
- Every `ingredientItems[*].ingredientId` MUST exactly match an existing key in `ingredientPrices`.
- Do not invent, rename, singularize, or pluralize ingredient IDs between sections.
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
      "mealType": "Breakfast",
      "difficulty": "Easy",
      "instructions": "Step-by-step instructions in one string.",
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
      "ingredients": ["Rolled Oats"]
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


def call_gemini(prompt: str, retries: int = DEFAULT_RETRIES) -> GeminiResponse:
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            raw_text = _generate_raw_response(prompt)
            json_text = _extract_json_text(raw_text)
            payload = json.loads(json_text)
            return GeminiResponse(**payload)
        except Exception as exc:
            last_error = exc
            print(f"Gemini attempt {attempt}/{retries} failed: {exc}")

    raise ValueError(f"Gemini failed after {retries} attempts: {last_error}")


def generate_meal_plan(preferences: dict[str, Any], retries: int = DEFAULT_RETRIES) -> GeminiResponse:
    prompt = build_prompt(preferences)
    return call_gemini(prompt, retries=retries)
    
