import { NextResponse } from 'next/server';
import { GoogleGenerativeAI } from "@google/generative-ai";
import fs from 'fs';
import path from 'path';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

export async function POST(request: Request) {
  try {
    const preferences = await request.json();
    const timestamp = new Date().toLocaleString('en-US', { 
      month: 'long', day: 'numeric', year: 'numeric', 
      hour: 'numeric', minute: 'numeric', second: 'numeric', 
      hour12: true, timeZoneName: 'short' 
    });

    // 1. Save preferences locally
    const prefPath = path.join(process.cwd(), 'user-preferences.json');
    fs.writeFileSync(prefPath, JSON.stringify(preferences, null, 2));

    const model = genAI.getGenerativeModel({ 
        model: "gemini-2.5-flash",
        generationConfig: { responseMimeType: "application/json" }
    });

    // 3. Create the Prompt
    const prompt = `
      You are a professional nutritionist. Create a 4-week meal plan (28 days) based on: ${JSON.stringify(preferences)}.
      Current Timestamp: ${timestamp}

      For EVERY meal, follow this EXACT JSON structure:
      {
        "weeks": [
          {
            "weekNumber": 1,
            "meals": [
              {
                "id": "unique-uuid",
                "day": "Monday",
                "name": "string",
                "calories": number,
                "carbs": "string (e.g. 79g)",
                "fat": "string (e.g. 23g)",
                "protein": "string (e.g. 44g)",
                "prepTime": number (minutes),
                "cookTime": number (minutes),
                "servings": number,
                "costPerServing": number,
                "totalCost": number,
                "mealType": "lunch" | "dinner" | "breakfast",
                "difficulty": "Easy" | "Medium" | "Hard",
                "ingredients": ["string"],
                "instructions": ["string"],
                "nutritionInfo": {
                  "calories": "string",
                  "carbs": "string",
                  "fat": "string",
                  "protein": "string"
                },
                "tags": ["string"],
                "tips": ["string"],
                "source": "generated",
                "createdAt": "${timestamp}",
                "updatedAt": "${timestamp}"
              }
            ]
          }
        ]
      }

      Requirements:
      - Strictly observe budget: $${preferences.monthlyBudget} total.
      - Strictly avoid: ${preferences.allergies.join(', ')} and ${preferences.excludedCuisines.join(', ')}.
      - Adjust calories for goal: ${preferences.goal} and weight: ${preferences.currentWeight}.
    `;

    const result = await model.generateContent(prompt);
    const mealPlanJSON = JSON.parse(result.response.text());

    // 2. Save the result locally for VS Code
    const planPath = path.join(process.cwd(), 'generated-meal-plan.json');
    fs.writeFileSync(planPath, JSON.stringify(mealPlanJSON, null, 2));

    return NextResponse.json(mealPlanJSON);

  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json({ error: 'Failed to generate' }, { status: 500 });
  }
}