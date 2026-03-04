from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai
import os
import json

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

class IngredientPrice(BaseModel):
    name: str
    category: str
    avgPrice: float
    unit: str

class GeminiResponse(BaseModel):
    mealPlan: list[Meal]
    ingredientPrices: dict[str, IngredientPrice]

def build_prompt(preferences: dict) -> str:
    return f"""
You are a professional nutritionist and chef. Generate a monthly meal plan
containing 28 meals total (breakfast, lunch, and dinner across 4 weeks,
one representative day per week shown).

User preferences:
- Monthly budget: ${preferences.get('monthlyBudget')}
- Goal: {preferences.get('goalType')}
- Dietary tags: {preferences.get('dietaryTags', [])}
- Allergies (strictly exclude): {preferences.get('allergies', [])}

Rules:
- Each meal must not exceed 2.5% of the monthly budget
- Strictly exclude any allergens listed above
- Vary meals across weeks to avoid repetition
- Include a mix of breakfast, lunch, and dinner meals

Return ONLY valid JSON with this exact structure, no extra text:
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
            "costPerServing": 2.50,
            "mealType": "Breakfast",
            "difficulty": "Easy",
            "instructions": "Step by step instructions as a single string",
            "tags": ["budget-friendly"],
            "tips": "A helpful tip",
            "source": "generated",
            "ingredientItems": [
                {{
                    "ingredientId": "ingredient_name",
                    "originalText": "1 cup rolled oats",
                    "quantity": 1,
                    "unit": "cup",
                    "notes": ""
                }}
            ],
            "ingredients": ["Ingredient Name"]
        }}
    ],
    "ingredientPrices": {{
        "ingredient_id": {{
            "name": "Ingredient Name",
            "category": "Grains",
            "avgPrice": 0.06,
            "unit": "cup"
        }}
    }}
}}
"""

def call_gemini(prompt: str, retries: int = 3) -> dict:
    """
    Calls Gemini API with retry logic.
    Strips markdown fences if present before parsing JSON.
    Raises ValueError if all retries fail.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash-lite",
        generation_config={"response_mime_type": "application/json"}
    )

    last_error = None
    for attempt in range(retries):
        try:
            result = model.generate_content(prompt)
            text = result.text.strip()
            # Strip markdown fences if Gemini wraps response in ```json ... ```
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            last_error = e
            print(f"Gemini attempt {attempt + 1} failed: {e}")

    raise ValueError(f"Gemini failed after {retries} attempts: {last_error}")

def generate_meal_plan(preferences: dict) -> GeminiResponse:
    """
    Builds prompt, calls Gemini, validates response against
    Pydantic schema. Raises ValueError if response is malformed.
    """
    prompt = build_prompt(preferences)
    raw = call_gemini(prompt)

    try:
        return GeminiResponse(**raw)
    except Exception as e:
        raise ValueError(f"Gemini response failed Pydantic validation: {e}")
    


