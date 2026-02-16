'use client';

import { useState, useEffect } from 'react';
import { Header } from '../../components/Header';
import { Footer } from '../../components/Footer';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { ImageWithFallback } from '../../components/figma/ImageWithFallback';
import { MealPlanWizard, MealPlanData } from '../../components/MealPlanWizard';
import Link from 'next/link';
import { Clock, DollarSign, Users, ChefHat, Calendar } from 'lucide-react';
import { generateMealPlan, saveMealPlan, loadMealPlan, clearMealPlan, FullMealPlan } from '../../utils/mealPlanGenerator';

export default function Dashboard() {
  const [mealPlan, setMealPlan] = useState<FullMealPlan | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState(1);

  useEffect(() => {
    const existingPlan = loadMealPlan();
    if (existingPlan) {
      setMealPlan(existingPlan);
    }
  }, []);

  const handleCreateMealPlan = (data: MealPlanData) => {
    const newPlan = generateMealPlan(data);
    saveMealPlan(newPlan);
    setMealPlan(newPlan);
    setShowWizard(false);
    setSelectedWeek(1);
  };

  const handleGenerateNew = () => {
    clearMealPlan();
    setMealPlan(null);
    setShowWizard(true);
  };

  if (!mealPlan) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
        <Header />
        <main className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto text-center">
            <ChefHat className="w-16 h-16 text-primary mx-auto mb-6" />
            <h1 className="text-3xl md:text-4xl text-primary mb-4">
              Welcome to Your Meal Planner
            </h1>
            <p className="text-lg text-muted-foreground mb-8">
              Let's create a personalized 4-week meal plan tailored to your budget, goals, and dietary needs.
            </p>
            <Button
              size="lg"
              onClick={() => setShowWizard(true)}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              Create Your Meal Plan
            </Button>
          </div>
        </main>
        <Footer />
        {showWizard && (
          <MealPlanWizard
            onComplete={handleCreateMealPlan}
            onCancel={() => setShowWizard(false)}
          />
        )}
      </div>
    );
  }

  const currentWeek = mealPlan.weeks[selectedWeek - 1];
  const totalWeeklyCost = currentWeek.meals.reduce((sum, meal) => sum + parseFloat(meal.cost.replace('$', '')), 0);
  const avgCostPerMeal = totalWeeklyCost / currentWeek.meals.length;
  const avgPrepTime = currentWeek.meals.reduce((sum, meal) => sum + parseInt(meal.prepTime), 0) / currentWeek.meals.length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
      <Header />
      <main className="container mx-auto px-4 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl text-primary mb-2">Your Meal Plan</h1>
          <p className="text-muted-foreground">
            Personalized recipes optimized for your ${mealPlan.preferences.monthlyBudget}/month budget
          </p>
        </div>

        {/* Week Selector */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-primary" />
            <h2 className="text-xl">Select Week</h2>
          </div>
          <div className="flex gap-2 flex-wrap">
            {mealPlan.weeks.map((week) => (
              <Button
                key={week.weekNumber}
                variant={selectedWeek === week.weekNumber ? 'default' : 'outline'}
                onClick={() => setSelectedWeek(week.weekNumber)}
                className={selectedWeek === week.weekNumber ? 'bg-primary hover:bg-primary/90' : ''}
              >
                Week {week.weekNumber}
              </Button>
            ))}
          </div>
        </div>

        {/* Weekly Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <DollarSign className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <CardDescription>Weekly Cost</CardDescription>
                  <CardTitle className="text-2xl">${totalWeeklyCost.toFixed(2)}</CardTitle>
                </div>
              </div>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <ChefHat className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <CardDescription>Avg. Cost Per Meal</CardDescription>
                  <CardTitle className="text-2xl">${avgCostPerMeal.toFixed(2)}</CardTitle>
                </div>
              </div>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Users className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <CardDescription>Servings Per Meal</CardDescription>
                  <CardTitle className="text-2xl">4</CardTitle>
                </div>
              </div>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <CardDescription>Avg. Prep Time</CardDescription>
                  <CardTitle className="text-2xl">{Math.round(avgPrepTime)} min</CardTitle>
                </div>
              </div>
            </CardHeader>
          </Card>
        </div>

        {/* Meal Plan Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {currentWeek.meals.map((meal) => (
            <Link key={meal.id} href={`/recipe/${meal.id}`}>
              <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer h-full">
                <div className="relative h-48">
                  <ImageWithFallback
                    src={meal.image}
                    alt={meal.name}
                    className="w-full h-full object-cover"
                  />
                  <Badge className="absolute top-3 right-3 bg-primary text-primary-foreground">
                    {meal.day}
                  </Badge>
                </div>
                <CardHeader>
                  <CardTitle className="text-xl">{meal.name}</CardTitle>
                  <CardDescription>{meal.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="w-4 h-4" />
                      <span>{meal.prepTime}</span>
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <DollarSign className="w-4 h-4" />
                      <span>{meal.cost}</span>
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Users className="w-4 h-4" />
                      <span>{meal.servings} servings</span>
                    </div>
                  </div>
                  <div className="mt-3">
                    <Badge variant="secondary" className="text-xs">
                      {meal.calories} cal
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            size="lg"
            onClick={handleGenerateNew}
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            Generate New Plan
          </Button>
          <Button size="lg" variant="outline" className="border-primary text-primary hover:bg-accent">
            Download Shopping List
          </Button>
        </div>
      </main>
      <Footer />
      {showWizard && (
        <MealPlanWizard
          onComplete={handleCreateMealPlan}
          onCancel={() => setShowWizard(false)}
        />
      )}
    </div>
  );
}
