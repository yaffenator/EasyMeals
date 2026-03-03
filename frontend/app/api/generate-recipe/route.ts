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
    const { mealName, preferences } = await request.json(); // Accept single meal context
    const timestamp = new Date().toISOString();

    const model = genAI.getGenerativeModel({
      model: 'gemini-3-flash-preview',
      generationConfig: { responseMimeType: 'application/json' },
    });

    // Prompt focused on hydrating ONE specific meal
    const prompt = `
      You are a professional chef. Provide full recipe details for the meal: "${mealName}".
      User Preferences: ${JSON.stringify(preferences)}
      Make sure not to excees 60% of the users budget for the mothly meal cost total.

      Return ONLY valid JSON in this exact format:
      {
        "name": "${mealName}",
        "description": "Detailed summary",
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
        "instructions": ["Step 1...", "Step 2..."],
        "ingredients": ["1 lb Salmon", "2 cloves Garlic"],
        "ingredientItems": [
          { "ingredientId": "salmon", "originalText": "1 lb Salmon", "quantity": 1, "unit": "lb" }
        ],
        "tags": ["high-protein"],
        "tips": ["Don't overcook the salmon"],
        "status": "completed"
      }
    `;

    const result = await model.generateContent(prompt);
    const fullMeal = JSON.parse(result.response.text());

    return NextResponse.json({
      ...fullMeal,
      updatedAt: timestamp
    });
  } catch (error) {
    return NextResponse.json({ error: 'Hydration failed' }, { status: 500 });
  }
}
