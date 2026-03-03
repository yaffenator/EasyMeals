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
/*
    const prompt = `
      You are a nutritionist and database architect. Create a 4-week meal plan, just focusing on making dinners.
      Use these preferneces to guide the meal plan, ensuring there are no mismatched between what the user wants and what is outputted: ${JSON.stringify(preferences)}
      
      BUDGET RULE: Total cost must not exceed 60% of $${preferences.monthlyBudget}.

      The average price for ingredients should be in USD and reflect current market prices. Use the following categories for ingredients: Produce, Meat, Dairy, Grains, Spices, etc.
      
      OUTPUT FORMAT: Return a JSON object with two keys: "mealPlan" and "newIngredients".
      
      1. "mealPlan": A 4-week plan. Each meal must follow your Firebase Recipe Schema:
         - "name", "calories", "carbs", "fat", "protein", "prepTime", "cookTime", "servings", "costPerServing", "totalCost", "mealType", "difficulty", "instructions", "tags", "tips", "source": "generated"
         - "ingredientItems": An array of maps: { "ingredientId": "snake_case_id", "originalText": "string", "quantity": number, "unit": "string", "notes": "string" }
         - "ingredients": A simple string array of the items.
         - "createdAt": "${timestamp}", "updatedAt": "${timestamp}"

      2. "newIngredients": A master list of every unique ingredient used in the recipes:
         { 
           "snake_case_id": { 
             "name": "Display Name", 
             "category": "Produce|Meat|Dairy|etc", 
             "avgPrice": number, 
             "unit": "standard unit" 
           } 
         }

      Ensure all ingredientIds are consistent between the recipes and the newIngredients list.
    `;
    

    const prompt = `
      You are a nutritionist and database architect. Create a 1 day meal plan, just focusing on making dinners.
      use these preferneces to guide the meal plan, ensuring there are no mismatched between what the user wants and what is outputted: ${JSON.stringify(preferences)}
      BUDGET RULE: Total cost must not exceed 60% of $${preferences.monthlyBudget}.

      OUTPUT FORMAT: Return a JSON object with the key: "mealPlan"

      1. "mealPlan": A 1-day plan. Each meal must follow our Firebase Recipe Schema:
         - "name", "calories", "carbs", "fat", "protein", "prepTime", "cookTime", "servings", "costPerServing", "totalCost", "mealType", "difficulty", "instructions", "tags", "tips", "source": "generated"
         - "ingredientItems": An array of maps: { "ingredientId": "snake_case_id", "originalText": "string", "quantity": number, "unit": "string", "notes": "string" }
         - "ingredients": A simple string array of the items.
         - "createdAt": "${timestamp}", "updatedAt": "${timestamp}"
    `;
*/
    const prompt = `
      Create a 4-week list of meal NAMES only.
      use these preferneces to guide the meals, ensuring there are no mismatched between what the user wants and what is outputted: ${JSON.stringify(preferences)}
      example format for returnd JSON: 
      {
        "weeks": [
          {
            "weekNumber": 1,
            "meals": [
              { "day": "Monday", "name": "Honey Garlic Salmon", "status": "pending" },
              ...
            ]
          }
        ]
      }
    `;

    const result = await model.generateContent(prompt);
    const responseData = JSON.parse(result.response.text());

    // Save user preferences to user-preferences.json
    fs.writeFileSync(path.join(process.cwd(), 'user-preferences.json'), JSON.stringify(preferences, null, 2));

    // Save locally for your review in VS Code
    fs.writeFileSync(path.join(process.cwd(), 'ai-response.json'), JSON.stringify(responseData, null, 2));

    return NextResponse.json(responseData);
  } catch (error) {
    console.error('Save preferences error:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: 'Generation failed', details: errorMessage }, { status: 500 });
  }
}