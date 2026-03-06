'use client';

import Link from 'next/link';

import { useMealPlan } from '../context/MealPlanContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

type DebugMeal = {
  id?: string;
  day?: string;
  name?: string;
};

type DebugWeek = {
  weekNumber?: number;
  weekIndex?: number;
  meals?: DebugMeal[];
};

export default function DebugPage() {
  const { mealPlan, isLoading } = useMealPlan();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-4">Debug: Loading Plan</h1>
          <p>Fetching latest plan from backend...</p>
        </div>
      </div>
    );
  }

  if (!mealPlan || !mealPlan.weeks?.length) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-4">Debug: No Meal Plan</h1>
          <p>Create a meal plan first on the dashboard.</p>
        </div>
      </div>
    );
  }

  const debugWeeks = mealPlan.weeks as DebugWeek[];

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Backend Meal-to-ID Mapping</h1>

        {debugWeeks.map((week, index) => {
          const weekNumber = week.weekNumber || (week.weekIndex ?? index) + 1;
          const meals = week.meals || [];

          return (
            <div key={weekNumber} className="mb-8">
              <h2 className="text-2xl font-semibold mb-4">Week {weekNumber}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {meals.map((meal, mealIndex) => (
                  <Card key={meal.id || `week-${weekNumber}-meal-${mealIndex}`} className="overflow-hidden">
                    <CardHeader>
                      <CardTitle className="text-lg">{meal.name || 'Unnamed Meal'}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="text-sm">
                        <span className="font-semibold">Day:</span> {meal.day || 'N/A'}
                      </div>
                      <div className="text-sm">
                        <span className="font-semibold">ID:</span>{' '}
                        <code className="bg-gray-100 px-2 py-1 rounded">
                          {meal.id || 'missing-id'}
                        </code>
                      </div>
                      <div className="text-sm">
                        <span className="font-semibold">URL:</span>{' '}
                        <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                          /recipe/{meal.id || 'missing-id'}
                        </code>
                      </div>
                      {meal.id && (
                        <Link
                          href={`/recipe/${meal.id}`}
                          className="text-blue-500 hover:underline text-sm font-semibold mt-2 inline-block"
                        >
                          View Recipe →
                        </Link>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
