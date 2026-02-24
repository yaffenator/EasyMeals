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
        model: "gemini-1.5-flash",
        generationConfig: { responseMimeType: "application/json" }
    });

    const prompt = `
      You are a nutritionist and database architect. Create a 4-week meal plan.
      User Preferences: ${JSON.stringify(preferences)}
      
      BUDGET RULE: Total cost must not exceed 60% of $${preferences.monthlyBudget}.
      
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

    const result = await model.generateContent(prompt);
    const responseData = JSON.parse(result.response.text());

    // Save locally for your review in VS Code
    fs.writeFileSync(path.join(process.cwd(), 'ai-response.json'), JSON.stringify(responseData, null, 2));

    return NextResponse.json(responseData);
  } catch (error) {
    return NextResponse.json({ error: 'Generation failed' }, { status: 500 });
  }
}