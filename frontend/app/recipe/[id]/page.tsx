'use client';

import { use, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from '../../components/dashboard-heading';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import ImageWithFallback from '../../components/Figma/imageWithFallback';
import { Clock, DollarSign, Users, ChefHat, ArrowLeft, Flame, Loader2, Lightbulb } from 'lucide-react';
import { useMealPlan } from '../../context/MealPlanContext'; // Import the context
import { generateRecipeDetails } from '../../utils/recipeDetails';
import Link from 'next/link';

export default function Recipe({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  
  // 1. Grab the global mealPlan and the loading status from context
  const { mealPlan } = useMealPlan();

  // 2. Find the recipe directly from the global state
  // This is reactive: if status changes from 'pending' to 'completed' in the background, 
  // this variable updates and the UI re-renders automatically.
  let recipe = null;
  if (mealPlan) {
    for (const week of mealPlan.weeks) {
      recipe = week.meals.find((meal: any) => meal.id === id) || null;
      if (recipe) break;
    }
  }

  // 3. Handle navigation if the recipe truly doesn't exist
  useEffect(() => {
    // Only redirect if we have a mealPlan loaded and still can't find the ID
    if (mealPlan && !recipe) {
      router.push('/dashboard');
    }
  }, [mealPlan, recipe, router]);

  // 4. Loading state for initial data fetch
  if (!mealPlan) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
      </div>
    );
  }

  // 5. "Still Generating" state
  // Because we use the global context, as soon as the background worker 
  // finishes this meal, this 'if' will become false and the recipe will pop in!
  if (!recipe || recipe.status === 'pending') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
        <Header />
        <main className="container mx-auto px-4 py-16 text-center">
          <div className="max-w-md mx-auto bg-white p-8 rounded-xl shadow-sm border">
            <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-primary">Chef is Writing the Recipe...</h1>
            <p className="text-muted-foreground mt-2">
              We are calculating the exact ingredients and costs for <b>{recipe?.name || 'this meal'}</b>. 
              This page will update automatically.
            </p>
            <Link href="/dashboard">
              <Button variant="outline" className="mt-6">Back to Dashboard</Button>
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const detailedRecipe = generateRecipeDetails(recipe);

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <Link href="/dashboard">
          <Button variant="ghost" className="mb-6 text-primary hover:text-primary/80">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Meal Plan
          </Button>
        </Link>

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Badge className="bg-primary text-primary-foreground">{detailedRecipe.day}</Badge>
                <Badge variant="outline">{detailedRecipe.difficulty || 'Easy'}</Badge>
              </div>
              <h1 className="text-3xl md:text-4xl text-primary mb-4">{detailedRecipe.name}</h1>
              <p className="text-lg text-muted-foreground">{detailedRecipe.description}</p>
            </div>

            <div className="relative w-full h-[400px] rounded-lg overflow-hidden border bg-muted">
              <ImageWithFallback
                src={detailedRecipe.image}
                alt={detailedRecipe.name}
                className="w-full h-full object-cover"
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card><CardContent className="pt-6 flex flex-col items-center text-center">
                <Clock className="w-6 h-6 text-primary mb-2" />
                <div className="text-xl font-bold mb-1">{detailedRecipe.prepTime}</div>
                <div className="text-sm text-muted-foreground">Prep Time</div>
              </CardContent></Card>

              <Card><CardContent className="pt-6 flex flex-col items-center text-center">
                <Users className="w-6 h-6 text-primary mb-2" />
                <div className="text-xl font-bold mb-1">{detailedRecipe.servings}</div>
                <div className="text-sm text-muted-foreground">Servings</div>
              </CardContent></Card>

              <Card><CardContent className="pt-6 flex flex-col items-center text-center">
                <DollarSign className="w-6 h-6 text-primary mb-2" />
                <div className="text-xl font-bold mb-1">{detailedRecipe.totalCost}</div>
                <div className="text-xs text-muted-foreground">{detailedRecipe.costPerServing}/serving</div>
              </CardContent></Card>

              <Card><CardContent className="pt-6 flex flex-col items-center text-center">
                <Flame className="w-6 h-6 text-primary mb-2" />
                <div className="text-xl font-bold mb-1">{detailedRecipe.calories}</div>
                <div className="text-sm text-muted-foreground">Calories</div>
              </CardContent></Card>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-primary">
                    <ChefHat className="w-5 h-5" /> Ingredients
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {detailedRecipe.ingredients?.map((ing: string, i: number) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-primary mt-1.5">-</span><span>{ing}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-primary">Instructions</CardTitle></CardHeader>
                <CardContent>
                  <ol className="space-y-4">
                    {detailedRecipe.instructions?.map((ins: string, i: number) => (
                      <li key={i} className="flex gap-4">
                        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">{i + 1}</span>
                        <span className="pt-1">{ins}</span>
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-primary">Nutrition Facts</CardTitle>
                <p className="text-sm text-muted-foreground">Per serving</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm">Calories</span><span className="text-lg font-bold">{detailedRecipe.calories}</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm"><span>Protein</span><span className="font-medium">{detailedRecipe.protein}</span></div>
                  <div className="flex justify-between text-sm"><span>Carbs</span><span className="font-medium">{detailedRecipe.carbs}</span></div>
                  <div className="flex justify-between text-sm"><span>Fat</span><span className="font-medium">{detailedRecipe.fat}</span></div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-primary flex items-center gap-2">
                  <Lightbulb className="w-5 h-5" /> Tips
                </CardTitle>
              </CardHeader>
              <CardContent>
                {detailedRecipe.tips?.length ? (
                  <ul className="space-y-2">
                    {detailedRecipe.tips.map((tip: string, i: number) => (
                      <li key={i} className="text-sm text-muted-foreground">{i + 1}. {tip}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No extra tips for this recipe.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}