'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '../../components/dashboard-heading';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Separator } from '../../components/ui/separator';
import ImageWithFallback from '../../components/Figma/imageWithFallback';
import { Clock, DollarSign, Users, ChefHat, ArrowLeft, Flame, Heart } from 'lucide-react';
import { loadMealPlan } from '../../utils/MealPlanGenerator';
import { generateRecipeDetails } from '../../utils/recipeDetails';
import Link from 'next/link';

export default function Recipe({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);

  // Load meal plan and find the recipe
  const mealPlan = loadMealPlan();
  
  if (!mealPlan) {
    router.push('/dashboard');
    return null;
  }

  // Find the recipe across all weeks
  let recipe = null;
  for (const week of mealPlan.weeks) {
    recipe = week.meals.find(meal => meal.id === id);
    if (recipe) break;
  }

  if (!recipe) {
    router.push('/dashboard');
    return null;
  }

  // Generate full recipe details
  const detailedRecipe = generateRecipeDetails(recipe);

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
      <Header />
      <main className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <Link href="/dashboard">
          <Button variant="ghost" className="mb-6 text-primary hover:text-primary/80">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Meal Plan
          </Button>
        </Link>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recipe Header */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Badge className="bg-primary text-primary-foreground">{detailedRecipe.day}</Badge>
                <Badge variant="outline">{detailedRecipe.difficulty}</Badge>
              </div>
              <h1 className="text-3xl md:text-4xl text-primary-black mb-4">{detailedRecipe.name}</h1>
              <p className="text-lg text-muted-foreground">{detailedRecipe.description}</p>
            </div>

            {/* Recipe Image */}
            <div className="relative w-full h-[400px] rounded-lg overflow-hidden">
              <ImageWithFallback
                src={detailedRecipe.image}
                alt={detailedRecipe.name}
                className="w-full h-full object-cover"
              />
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <Clock className="w-6 h-6 text-primary mb-2" />
                    <div className="text-2xl mb-1">{detailedRecipe.prepTime}</div>
                    <div className="text-sm text-muted-foreground">Prep Time</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <Users className="w-6 h-6 text-primary mb-2" />
                    <div className="text-2xl mb-1">{detailedRecipe.servings}</div>
                    <div className="text-sm text-muted-foreground">Servings</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <DollarSign className="w-6 h-6 text-primary mb-2" />
                    <div className="text-2xl mb-1">{detailedRecipe.cost}</div>
                    <div className="text-sm text-muted-foreground">Cost</div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <Flame className="w-6 h-6 text-primary mb-2" />
                    <div className="text-2xl mb-1">{detailedRecipe.calories}</div>
                    <div className="text-sm text-muted-foreground">Calories</div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Ingredients */}
            <div className="grid md:grid-cols-2 gap-8">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-primary">
                    <ChefHat className="w-5 h-5" />
                    Ingredients
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {detailedRecipe.ingredients.map((ingredient, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-primary mt-1.5">•</span>
                        <span>{ingredient}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              {/* Instructions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-primary">Instructions</CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="space-y-4">
                    {detailedRecipe.instructions.map((instruction, index) => (
                      <li key={index} className="flex gap-4">
                        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/90 text-primary-foreground flex items-center justify-center">
                          {index + 1}
                        </span>
                        <span className="pt-1">{instruction}</span>
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            </div>

            {/* Tips */}
            <Card className="bg-accent/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-primary">
                  <Heart className="w-5 h-5" />
                  Chef's Tips
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {detailedRecipe.tips.map((tip, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-primary mt-1.5">💡</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Nutrition Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-primary">Nutrition Facts</CardTitle>
                <p className="text-sm text-muted-foreground">Per serving</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm">Calories</span>
                  <span className="text-lg">{detailedRecipe.calories}</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Protein</span>
                    <span>{detailedRecipe.protein}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Carbohydrates</span>
                    <span>{detailedRecipe.carbs}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Fat</span>
                    <span>{detailedRecipe.fat}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Dietary Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-primary">Your Preferences</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Goal</p>
                  <Badge variant="secondary" className="capitalize">
                    {mealPlan.preferences.goal === 'lose' ? 'Lose Weight' : 
                     mealPlan.preferences.goal === 'gain' ? 'Gain Weight' : 
                     'Maintain Weight'}
                  </Badge>
                </div>
                <Separator />
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Budget</p>
                  <p className="text-lg">${mealPlan.preferences.monthlyBudget}/month</p>
                </div>
                {mealPlan.preferences.allergies.length > 0 && (
                  <>
                    <Separator />
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Avoiding</p>
                      <div className="flex flex-wrap gap-1">
                        {mealPlan.preferences.allergies.slice(0, 5).map((allergy, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {allergy}
                          </Badge>
                        ))}
                        {mealPlan.preferences.allergies.length > 5 && (
                          <Badge variant="outline" className="text-xs">
                            +{mealPlan.preferences.allergies.length - 5} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="space-y-4">
              <Card className="bg-primary/5">
                <CardContent className="pt-6 space-y-3">
                  <Button className="w-full bg-primary hover:bg-primary/90">
                    Add to Shopping List
                  </Button>
                  <Button variant="outline" className="w-full border-primary text-primary hover:bg-accent">
                    Save Recipe
                  </Button>
                </CardContent>
              </Card>

              {/* Rate this Meal - Interactive version */}
              <div className="px-2 pt-2 text-center lg:text-left">
                <p className="text-sm font-medium text-muted-foreground mb-3 uppercase tracking-wider">
                  Rate this meal
                </p>
                <div className="flex items-center gap-1 justify-center lg:justify-start">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      className="transition-all duration-150 hover:scale-125 active:scale-95 focus:outline-none"
                      onClick={() => setRating(star)}
                      onMouseEnter={() => setHover(star)}
                      onMouseLeave={() => setHover(0)}
                    >
                      <Heart 
                        className={`w-7 h-7 transition-colors ${
                          star <= (hover || rating)
                            ? "fill-primary text-primary" 
                            : "text-muted-foreground/30"
                        }`} 
                      />
                    </button>
                  ))}
                  
                  {/* Display the value */}
                  <span className="ml-3 text-lg font-bold text-primary">
                    {rating > 0 ? rating.toFixed(1) : "0.0"}
                  </span>
                </div>
                
                {rating > 0 && (
                  <p className="text-xs text-primary mt-2 animate-in fade-in slide-in-from-top-1">
                    Thanks for your feedback!
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
