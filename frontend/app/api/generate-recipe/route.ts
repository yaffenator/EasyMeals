import { NextResponse } from 'next/server';
import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

interface GeneratedMeal {
  day?: string;
  name?: string;
  mealType?: string;
  source?: string;
  [key: string]: unknown;
}

interface GeneratedWeek {
  weekNumber?: number;
  meals?: GeneratedMeal[];
}

interface ModelResponse {
  weeks?: GeneratedWeek[];
  mealPlan?: { weeks?: GeneratedWeek[] };
}

export async function POST(request: Request) {
  try {
    const preferences = await request.json();
    const timestamp = new Date().toISOString();

    const model = genAI.getGenerativeModel({
      model: 'gemini-3-flash-preview',
      generationConfig: { responseMimeType: 'application/json' },
    });

    const prompt = `
      You are a nutritionist and meal planner. Build a complete 4-week dinner meal plan.
      Use these preferences and respect them strictly: ${JSON.stringify(preferences)}

      Budget rule: The total monthly cost of all meals must not exceed 60% of $${preferences.monthlyBudget}.

      make sure to be thurogh in the instruction steps, and include tips that are relevant to the recipe.
      also make sure not to forget seasonioongs and spices, as those are often the most missed items in meal planning.

      Return ONLY valid JSON in this exact format:
      {
        "weeks": [
          {
            "weekNumber": 1,
            "meals": [
              {
                "day": "Monday",
                "name": "Meal name",
                "description": "Short meal summary",
                "calories": 550,
                "carbs": "45g",
                "fat": "20g",
                "protein": "35g",
                "prepTime": "20 min",
                "cookTime": 25,
                "servings": 4,
                "costPerServing": "$3.50",
                "totalCost": "$14.00",
                "mealType": "Dinner",
                "difficulty": "Easy",
                "instructions": ["step 1", "step 2"],
                "ingredients": ["ingredient text"],
                "ingredientItems": [
                  {
                    "ingredientId": "ingredient_snake_case",
                    "originalText": "1 lb chicken breast",
                    "quantity": 1,
                    "unit": "lb",
                    "notes": "boneless"
                  }
                ],
                "tags": ["high-protein"],
                "tips": ["prep tip"],
                "source": "generated"
              }
            ]
          }
        ]
      }

      Requirements:
      - 4 weeks exactly.
      - 7 dinners per week (Monday through Sunday).
      - Include all listed fields for every meal.
      - Keep output JSON-only.
    `;

    const result = await model.generateContent(prompt);
    const parsed = JSON.parse(result.response.text()) as ModelResponse;
    const rawWeeks = parsed?.weeks || parsed?.mealPlan?.weeks;

    if (!Array.isArray(rawWeeks) || rawWeeks.length === 0) {
      throw new Error('Model response missing weeks array');
    }

    const weeks = rawWeeks.slice(0, 4).map((week, weekIndex) => {
      const weekNumber = Number(week?.weekNumber) || weekIndex + 1;
      const meals = Array.isArray(week?.meals) ? week.meals : [];

      return {
        weekNumber,
        meals: meals.slice(0, 7).map((meal, mealIndex) => ({
          ...meal,
          day: meal?.day || DAYS[mealIndex] || 'Monday',
          mealType: meal?.mealType || 'Dinner',
          source: meal?.source || 'generated',
          status: 'completed',
          createdAt: timestamp,
          updatedAt: timestamp,
        })),
      };
    });

    return NextResponse.json({
      mealPlan: {
        preferences,
        weeks,
        createdAt: timestamp,
      },
    });
  } catch (error) {
    console.error('Error in /api/generate-recipe:', error);
    return NextResponse.json({ error: 'Failed to generate meal plan' }, { status: 500 });
  }
}
