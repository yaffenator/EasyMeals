"use client";

import { useState, useEffect } from "react";
import DashboardHeading from "../components/dashboard-heading";
import { Footer } from "../components/footer";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import ImageWithFallback from "../components/Figma/imageWithFallback";
import { MealPlanWizard } from "../components/MealPlanWizard";
import Link from "next/link";
import { Clock, DollarSign, Calendar, Soup, ChefHat } from "lucide-react";
import { useAuth } from "../context/auth";
import { useRouter } from "next/navigation";
import { auth, db } from "../firebase";
import { doc, getDoc } from "firebase/firestore";
import { useMealPlan } from "../context/MealPlanContext"; // Import the context
import type { MealPlan } from "../context/MealPlanContext";

type DashboardMeal = {
  id?: string;
  day?: string;
  name?: string;
  description?: string;
  image?: string;
  prepTime?: string;
  totalCost?: string;
  costPerServing?: number | string;
  calories?: number;
  status?: string;
  imageGenStatus?: string;
};

type DashboardWeek = {
  weekNumber?: number;
  meals?: DashboardMeal[];
};

const parseMoney = (value: unknown): number => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value.replace("$", "").trim());
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

const parseMinutes = (value: unknown): number => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
};

const formatCurrency = (value: unknown): string =>
  `$${parseMoney(value).toFixed(2)}`;

const detailBadgeForMeal = (
  meal: DashboardMeal,
): { label: string; className: string } | null => {
  const status =
    typeof meal.status === "string" ? meal.status.toLowerCase() : "";
  if (status === "completed") return null;
  if (status === "failed") {
    return { label: "Details Failed", className: "bg-red-100 text-red-800" };
  }
  return {
    label: "Details Pending",
    className: "bg-amber-100 text-amber-800",
  };
};

const imageBadgeForMeal = (
  meal: DashboardMeal,
): { label: string; className: string } | null => {
  const value = meal.image;
  const trimmed = typeof value === "string" ? value.trim() : "";
  const hasUsableImage =
    !!trimmed &&
    !trimmed.startsWith("/api/placeholder") &&
    !trimmed.startsWith("/meal-placeholder");
  if (hasUsableImage) return null;

  const status =
    typeof meal.imageGenStatus === "string"
      ? meal.imageGenStatus.toLowerCase()
      : "";
  if (status === "failed") {
    return { label: "Image Failed", className: "bg-red-100 text-red-800" };
  }
  if (status === "pending") {
    return {
      label: "Image Pending",
      className: "bg-secondary text-secondary-foreground",
    };
  }
  return {
    label: "Image Pending",
    className: "bg-secondary text-secondary-foreground",
  };
};

export default function Dashboard() {
  // 1. Replace local state with Global Context
  const { mealPlan, setMealPlan, isLoading, refreshPlan, imageSyncStatus } =
    useMealPlan();

  const [showWizard, setShowWizard] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [questionnaireCompleted, setQuestionnaireCompleted] = useState(false);
  const [isRefreshingPlan, setIsRefreshingPlan] = useState(false);

  const router = useRouter();
  const { currentUser } = useAuth();
  const typedCurrentUser = currentUser as
    | { displayName?: string | null; email?: string | null }
    | null
    | undefined;

  // Auth check
  useEffect(() => {
    if (!currentUser && !auth.currentUser) {
      router.push("/login");
    }
  }, [currentUser, router]);

  // Check Firestore for questionnaire status
  useEffect(() => {
    const checkQuestionnaireStatus = async () => {
      const uid = auth.currentUser?.uid;
      if (uid) {
        try {
          const userRef = doc(db, "users", uid);
          const userSnap = await getDoc(userRef);
          if (userSnap.exists()) {
            const userData = userSnap.data();
            setQuestionnaireCompleted(
              !!userData.mealPlanProfile?.questionnaireCompleted,
            );
          }
        } catch (error) {
          console.error("Error fetching user data:", error);
        }
      }
    };
    checkQuestionnaireStatus();
  }, [currentUser, mealPlan]);

  // 2. The hydration logic (useEffect) has been REMOVED.
  // It now lives in MealPlanContext.tsx to allow background processing.

  const handleCreateMealPlan = (fullMealPlan: unknown) => {
    setMealPlan(fullMealPlan as MealPlan); // Updates the Global Context
    setQuestionnaireCompleted(true);
    setShowWizard(false);
  };

  const handleGenerateNew = () => {
    setMealPlan(null);
    setShowWizard(true);
  };

  const handleRefreshPlan = async () => {
    setIsRefreshingPlan(true);
    try {
      await refreshPlan();
    } finally {
      setIsRefreshingPlan(false);
    }
  };

  const displayName = auth.currentUser?.displayName || typedCurrentUser?.displayName;
  const emailName =
    auth.currentUser?.email?.split("@")[0] ||
    typedCurrentUser?.email?.split("@")[0] ||
    "Chef";
  const prefBudget =
    mealPlan &&
    mealPlan.preferences &&
    typeof mealPlan.preferences === "object" &&
    "monthlyBudget" in mealPlan.preferences
      ? mealPlan.preferences.monthlyBudget
      : mealPlan?.monthlyBudget;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
        <DashboardHeading />
        <main className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto text-center">
            <p className="text-lg text-muted-foreground">
              Loading your meal plan...
            </p>
          </div>
        </main>
      </div>
    );
  }

  // GUARD CLAUSE: Show "Create" prompt if no plan exists
  if (!questionnaireCompleted || !mealPlan || !mealPlan.weeks) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
        <DashboardHeading />
        <main className="container mx-auto px-4 py-16">
          <div className="max-w-2xl mx-auto text-center">
            <ChefHat className="w-16 h-16 text-primary mx-auto mb-6" />
            <h1 className="text-3xl md:text-4xl text-primary mb-4">
              Welcome, {displayName || "Chef"}!
            </h1>
            <p className="text-lg text-muted-foreground mb-8">
              It looks like you have not generated your personalized plan yet.
              Let&apos;s create a 4-week meal plan tailored to your budget and
              goals.
            </p>
            <Button
              size="lg"
              onClick={() => setShowWizard(true)}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              Create Your Meal Plan
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={handleRefreshPlan}
              disabled={isRefreshingPlan}
              className="ml-3"
            >
              {isRefreshingPlan ? "Checking..." : "Check for Completed Plan"}
            </Button>
          </div>
        </main>
        {showWizard && (
          <MealPlanWizard
            onComplete={handleCreateMealPlan}
            onCancel={() => setShowWizard(false)}
          />
        )}
      </div>
    );
  }

  // Calculate current view data
  const mealPlanWeeks = mealPlan.weeks as DashboardWeek[];
  const currentWeek = mealPlanWeeks[selectedWeek - 1] || { meals: [] };
  const currentWeekMeals = currentWeek.meals || [];

  const totalWeeklyCost = currentWeekMeals.reduce(
    (sum: number, meal: DashboardMeal) =>
      sum + parseMoney(meal.costPerServing ?? meal.totalCost ?? 0),
    0,
  );

  const avgPrepTime = currentWeekMeals.length
    ? currentWeekMeals.reduce(
        (sum: number, meal: DashboardMeal) => sum + parseMinutes(meal.prepTime),
        0,
      ) / currentWeekMeals.length
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-secondary/30">
      <DashboardHeading />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl text-primary mb-2">
            Hello, {displayName || emailName}!
          </h1>
          <p className="text-muted-foreground">
            Recipes optimized for your $
            {typeof prefBudget === "number" ? prefBudget : 0}/month budget
          </p>
          {(mealPlan.status || "").toLowerCase() === "generating" && (
            <p className="mt-2 text-sm text-muted-foreground">
              Building meal details in the background. Cards unlock as each meal
              completes.
            </p>
          )}
          {imageSyncStatus === "syncing" && (
            <p className="mt-2 text-sm text-muted-foreground">
              Generating meal images in the background. This page auto-refreshes
              every ~10 seconds.
            </p>
          )}
          {imageSyncStatus === "ready" && (
            <p className="mt-2 text-sm text-green-700">
              Meal images are ready.
            </p>
          )}
          {imageSyncStatus === "timeout" && (
            <p className="mt-2 text-sm text-amber-700">
              Image generation is taking longer than expected. Use Refresh Plan
              to check latest status.
            </p>
          )}
        </div>

        {/* Week Selector */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-primary" />
            <h2 className="text-xl">Select Week</h2>
          </div>
          <div className="flex gap-2 flex-wrap">
            {mealPlanWeeks.map((week: DashboardWeek, index: number) => {
              const weekNumber = week.weekNumber || index + 1;
              return (
                <Button
                  key={weekNumber}
                  variant={selectedWeek === weekNumber ? "default" : "outline"}
                  onClick={() => setSelectedWeek(weekNumber)}
                  className={selectedWeek === weekNumber ? "bg-primary" : ""}
                >
                  Week {weekNumber}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Weekly Cost</CardDescription>
              <CardTitle className="text-2xl">
                ${totalWeeklyCost.toFixed(2)}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Avg. Prep Time</CardDescription>
              <CardTitle className="text-2xl">
                {Math.round(avgPrepTime)} min
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Meal Plan Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {currentWeekMeals.map((meal: DashboardMeal, index: number) => {
            const imageBadge = imageBadgeForMeal(meal);
            const detailBadge = detailBadgeForMeal(meal);
            const isMealReady =
              typeof meal.status === "string"
                ? meal.status.toLowerCase() === "completed"
                : false;
            const card = (
              <Card
                className={`overflow-hidden transition-shadow h-full ${
                  isMealReady
                    ? "hover:shadow-lg cursor-pointer"
                    : "opacity-80 cursor-not-allowed"
                }`}
              >
                <div className="relative h-48">
                  <ImageWithFallback
                    src={meal.image || "/meal-placeholder.svg"}
                    alt={meal.name || "Meal image"}
                    className="w-full h-full object-cover"
                  />
                  <Badge className="absolute top-3 right-3 bg-primary text-primary-foreground">
                    {meal.day}
                  </Badge>
                  {imageBadge && (
                    <Badge
                      className={`absolute top-3 left-3 ${imageBadge.className}`}
                    >
                      {imageBadge.label}
                    </Badge>
                  )}
                  {detailBadge && (
                    <Badge className={`absolute bottom-3 left-3 ${detailBadge.className}`}>
                      {detailBadge.label}
                    </Badge>
                  )}
                </div>
                <CardHeader className="pb-0 pt-4">
                  <CardTitle className="text-xl">{meal.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {meal.description || "Meal details are still being generated."}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />{" "}
                      {meal.prepTime || (isMealReady ? "0 min" : "Pending")}
                    </div>
                    <div className="flex items-center gap-1">
                      <DollarSign className="w-4 h-4" />{" "}
                      {isMealReady
                        ? formatCurrency(meal.costPerServing ?? meal.totalCost)
                        : "Pending"}
                    </div>
                    <div className="flex items-center gap-1">
                      <Soup className="w-4 h-4" />{" "}
                      {isMealReady ? `${meal.calories || 0} cal` : "Pending"}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
            return (
              <div key={meal.id || `meal-${index}`} className="h-full">
                {isMealReady && meal.id ? (
                  <Link href={`/recipe/${meal.id}`}>{card}</Link>
                ) : (
                  card
                )}
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" onClick={handleGenerateNew}>
            Generate New Plan
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={handleRefreshPlan}
            disabled={isRefreshingPlan}
          >
            {isRefreshingPlan ? "Refreshing..." : "Refresh Plan"}
          </Button>
          <Button size="lg" variant="outline">
            Download Shopping List
          </Button>
        </div>
      </main>
    </div>
  );
}
