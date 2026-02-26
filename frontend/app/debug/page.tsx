'use client';

import { useEffect, useState } from 'react';
import { loadMealPlan, FullMealPlan } from '../utils/MealPlanGenerator';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import Link from 'next/link';

export default function DebugPage() {
  const [mealPlan, setMealPlan] = useState<FullMealPlan | null>(null);

  useEffect(() => {
    const plan = loadMealPlan();
    setMealPlan(plan);
  }, []);

  if (!mealPlan) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-4">Debug: No Meal Plan</h1>
          <p>Create a meal plan first on the dashboard.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Meal-to-ID Mapping</h1>
        
        {mealPlan.weeks.map((week) => (
          <div key={week.weekNumber} className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Week {week.weekNumber}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {week.meals.map((meal) => (
                <Card key={meal.id} className="overflow-hidden">
                  <CardHeader>
                    <CardTitle className="text-lg">{meal.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="text-sm">
                      <span className="font-semibold">Day:</span> {meal.day}
                    </div>
                    <div className="text-sm">
                      <span className="font-semibold">ID:</span> <code className="bg-gray-100 px-2 py-1 rounded">{meal.id}</code>
                    </div>
                    <div className="text-sm">
                      <span className="font-semibold">URL:</span> <code className="bg-gray-100 px-2 py-1 rounded text-xs">/recipe/{meal.id}</code>
                    </div>
                    <Link 
                      href={`/recipe/${meal.id}`}
                      className="text-blue-500 hover:underline text-sm font-semibold mt-2 inline-block"
                    >
                      View Recipe →
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
