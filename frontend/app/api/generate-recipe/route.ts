import { NextResponse } from 'next/server';
import { GoogleGenerativeAI } from "@google/generative-ai";
import fs from 'fs';
import path from 'path';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

export async function POST(request: Request) {
  try {
    const preferences = await request.json();
    const timestamp = new Date().toISOString(); // Using ISO for Firebase compatibility

    const model = genAI.getGenerativeModel({ 
        model: "gemini-3-flash-preview",
        generationConfig: { responseMimeType: "application/json" }
    });
  
    const prompt = `
        You are a nutritionist and database architect. Create one donner that will be used for a larger meal plan.
        use these preferneces to guide the meal plan, ensuring there are no mismatches between what the user wants and what is outputted: ${JSON.stringify(preferences)}
        BUDGET RULE: Total cost must not exceed 60% of $${preferences.monthlyBudget}.

        OUTPUT FORMAT: Return a JSON object with the key: "mealPlan"

        1. "mealPlan": A 1-day plan. Each meal must follow our Firebase Recipe Schema:
            - "name", "calories", "carbs", "fat", "protein", "prepTime", "cookTime", "servings", "costPerServing", "totalCost", "mealType", "difficulty", "instructions", "tags", "tips", "source": "generated"
            - "ingredientItems": An array of maps: { "ingredientId": "snake_case_id", "originalText": "string", "quantity": number, "unit": "string", "notes": "string" }
            - "ingredients": A simple string array of the items.
            - "createdAt": "${timestamp}", "updatedAt": "${timestamp}"
    `;

    const result = await model.generateContent(prompt);
    return NextResponse.json(JSON.parse(result.response.text()));
  } catch (error) {
    console.error("Error in /api/generate-recipe:", error);
    return NextResponse.json({ error: "Failed to generate meal plan" }, { status: 500 });
  }
}