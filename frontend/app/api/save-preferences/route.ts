import { NextResponse } from 'next/server';
import { GoogleGenerativeAI } from "@google/generative-ai";

export const maxDuration = 60;

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

export async function POST(request: Request) {
  try {
    const preferences = await request.json();
    
    // Using gemini-1.5-flash or your specified model
    const model = genAI.getGenerativeModel({ 
        model: "gemini-3-flash-preview", // Note: Ensure this is your intended model version!
        generationConfig: { responseMimeType: "application/json" }
    });

    const prompt = `
      Create a 4-week list of meal NAMES and short descriptions only.
      be sure to stick to these preferences strictly: ${JSON.stringify(preferences)}
      Return JSON:
      {
        "weeks": [
          {
            "weekNumber": 1,
            "meals": [
              { 
                "day": "Monday", 
                "name": "Honey Garlic Salmon", 
                "description": "Succulent salmon glazed in a sweet and savory garlic sauce.",
                "status": "pending" 
              }
            ]
          }
        ]
      }
    `;

    const result = await model.generateContent(prompt);
    const responseData = JSON.parse(result.response.text());

    // REMOVED the fs.writeFileSync lines here! Vercel will no longer crash.

    // Send the generated JSON directly back to your frontend
    return NextResponse.json(responseData);
  } catch (error) {
    console.error('Save preferences error:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}