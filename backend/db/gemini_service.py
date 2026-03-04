from pydantic import BaseModel
from typing import Optional

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