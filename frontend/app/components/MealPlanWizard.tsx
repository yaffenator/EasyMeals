"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { RadioGroup, RadioGroupItem } from "./ui/radioGroup";
import { Checkbox } from "./ui/checkbox";
import { ChevronRight, ChevronLeft, Loader2 } from "lucide-react";
import { updateUserPreferences, auth } from "../firebase";

interface MealPlanWizardProps {
  onComplete: (data: unknown) => void;
  onCancel: () => void;
}

export interface MealPlanData {
  monthlyBudget: number;
  goal: "lose" | "gain" | "maintain";
  currentWeight: number;
  allergies: string[];
  excludedCuisines: string[];
}

interface BackendMeal {
  [key: string]: unknown;
  day?: string;
  costPerServing?: number | string;
  carbs?: number | string;
  fat?: number | string;
  protein?: number | string;
}

interface BackendWeek {
  [key: string]: unknown;
  weekIndex?: number;
  meals?: BackendMeal[];
}

interface BackendGeneratePlanResponse {
  planId?: string;
  status?: string;
  monthlyBudget?: number;
  estimatedTotalCost?: number;
  groceryList?: unknown[];
  metadata?: Record<string, unknown>;
  weeks?: BackendWeek[];
}

const commonAllergies = [
  "Milk",
  "Eggs",
  "Peanuts",
  "Tree Nuts",
  "Soy",
  "Wheat",
  "Fish",
  "Shellfish",
  "Sesame",
  "Corn",
  "Gluten",
  "Mustard",
  "Sulfites",
];

export function MealPlanWizard({ onComplete, onCancel }: MealPlanWizardProps) {
  const [step, setStep] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const [monthlyBudget, setMonthlyBudget] = useState("");
  const [goal, setGoal] = useState<"lose" | "gain" | "maintain">("maintain");
  const [weight, setWeight] = useState("");
  const [selectedAllergies, setSelectedAllergies] = useState<string[]>([]);
  const [excludedCuisines, setExcludedCuisines] = useState("");
  const [timedOutGeneration, setTimedOutGeneration] = useState(false);

  const hasMaxDecimals = (value: string, maxDecimals: number): boolean => {
    if (!value.includes(".")) return true;
    const [, decimalPart] = value.split(".");
    return decimalPart.length <= maxDecimals;
  };

  const toCurrencyString = (value: unknown): string => {
    if (typeof value === "number") return `$${value.toFixed(2)}`;
    if (typeof value === "string") {
      return value.startsWith("$") ? value : `$${value}`;
    }
    return "$0.00";
  };

  const handleNext = async () => {
    setErrorMessage("");
    setTimedOutGeneration(false);

    if (step < 5) {
      setStep(step + 1);
      return;
    }

    setIsSaving(true);

    const finalData = {
      questionnaireCompleted: true,
      monthlyBudget: parseFloat(monthlyBudget),
      goal,
      currentWeight: parseFloat(weight),
      allergies: selectedAllergies,
      excludedCuisines: excludedCuisines
        .split(",")
        .map((c) => c.trim())
        .filter((c) => c !== ""),
    };

    try {
      const uid = auth.currentUser?.uid;
      if (!uid) throw new Error("No user ID found");
      const idToken = await auth.currentUser!.getIdToken();

      // 1. Update user profile in Firestore
      await updateUserPreferences(uid, finalData);

      const generationPayload = {
        userId: uid,
        monthlyBudget: Number.parseFloat(monthlyBudget),
        weight: Number.parseFloat(weight),
        goalType: goal,
        dietaryTags: [],
        allergies: selectedAllergies.map((allergy) => allergy.toLowerCase()),
      };

      // 2. Generate a full plan from backend
      const response = await fetch("/api/plan/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(generationPayload),
      });

      if (!response.ok) {
        let detail = "Plan generation failed";
        try {
          const errorData = await response.json();
          detail = errorData?.detail || detail;
        } catch {
          // Preserve default message when response is not JSON.
        }

        if (response.status === 409) {
          throw new Error(
            "A meal plan is already generating for your account. Please wait and retry.",
          );
        }
        if (response.status === 400) {
          throw new Error(`Please fix your inputs: ${detail}`);
        }
        if (response.status === 504) {
          setTimedOutGeneration(true);
          throw new Error(
            "Generation is taking longer than expected and may take up to ~3 minutes with the current model. Your request may still finish; use dashboard refresh after about 30 seconds.",
          );
        }
        throw new Error(detail);
      }

      const responseData =
        (await response.json()) as BackendGeneratePlanResponse;

      // 3. Transform backend response into current dashboard-compatible shape.
      const generatedMealPlan = {
        preferences: finalData,
        planId: responseData.planId,
        status: responseData.status,
        monthlyBudget: responseData.monthlyBudget,
        estimatedTotalCost: responseData.estimatedTotalCost,
        groceryList: responseData.groceryList || [],
        metadata: responseData.metadata || {},
        weeks: (responseData.weeks || []).map((week: BackendWeek) => ({
          ...week,
          weekNumber: (week.weekIndex ?? 0) + 1,
          meals: (week.meals || []).map((meal: BackendMeal, idx: number) => ({
            ...meal,
            day:
              meal.day ||
              [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
              ][idx % 7],
            instructions: Array.isArray(meal.instructions)
              ? meal.instructions
              : typeof meal.instructions === "string"
                ? meal.instructions
                : "",
            totalCost: toCurrencyString(meal.costPerServing),
            costPerServing: toCurrencyString(meal.costPerServing),
            carbs: meal.carbs != null ? `${meal.carbs}g` : "0g",
            fat: meal.fat != null ? `${meal.fat}g` : "0g",
            protein: meal.protein != null ? `${meal.protein}g` : "0g",
            status:
              typeof meal.status === "string" && meal.status.length > 0
                ? meal.status
                : "pending",
          })),
        })),
        createdAt: new Date().toISOString(),
      };

      // 4. Pass generated plan to parent (Dashboard)
      onComplete(generatedMealPlan);
    } catch (error) {
      console.error("Error during setup:", error);
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage(
          "Something went wrong. Please check your connection and try again.",
        );
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleBack = () => step > 1 && setStep(step - 1);

  const canProceed = () => {
    if (step === 1) {
      const budget = Number.parseFloat(monthlyBudget);
      return (
        monthlyBudget !== "" &&
        Number.isFinite(budget) &&
        budget >= 50 &&
        budget <= 1000 &&
        hasMaxDecimals(monthlyBudget, 2)
      );
    }
    if (step === 2) return !!goal;
    if (step === 3) {
      const currentWeight = Number.parseFloat(weight);
      return (
        weight !== "" &&
        Number.isFinite(currentWeight) &&
        currentWeight >= 100 &&
        currentWeight <= 380 &&
        hasMaxDecimals(weight, 1)
      );
    }
    return true;
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <CardHeader className="border-b">
          <CardTitle className="text-2xl text-primary">
            Meal Plan Setup
          </CardTitle>
          <CardDescription>Step {step} of 5</CardDescription>
        </CardHeader>

        <CardContent className="pt-6">
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">
                What is your monthly food budget?
              </h3>
              <div className="space-y-2">
                <Label htmlFor="budget">Budget in USD ($)</Label>
                <Input
                  id="budget"
                  type="number"
                  pattern="[0-9]*"
                  step="0.01"
                  min="50"
                  max="1000"
                  placeholder="400"
                  value={monthlyBudget}
                  onChange={(e) => setMonthlyBudget(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Enter a value from 50.00 to 1000.00 (max 2 decimals).
                </p>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">
                What is your primary goal?
              </h3>
              <RadioGroup
                value={goal}
                onValueChange={(v) =>
                  setGoal(v as "lose" | "gain" | "maintain")
                }
                className="grid gap-3"
              >
                {["lose", "maintain", "gain"].map((g) => (
                  <Label
                    key={g}
                    className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-secondary/20 cursor-pointer capitalize"
                  >
                    <RadioGroupItem value={g} />
                    <span>{g} Weight</span>
                  </Label>
                ))}
              </RadioGroup>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">
                What is your current weight?
              </h3>
              <div className="space-y-2">
                <Label htmlFor="weight">Weight (lbs)</Label>
                <Input
                  id="weight"
                  type="number"
                  step="0.1"
                  min="100"
                  max="380"
                  placeholder="165"
                  value={weight}
                  pattern="[0-9]*\.?[0-9]*"
                  onChange={(e) => setWeight(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Enter a value from 100.0 to 380.0 lbs (max 1 decimal).
                </p>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">Any food allergies?</h3>
              <div className="grid grid-cols-2 gap-3">
                {commonAllergies.map((a) => (
                  <div key={a} className="flex items-center space-x-2">
                    <Checkbox
                      id={a}
                      checked={selectedAllergies.includes(a)}
                      onCheckedChange={() =>
                        setSelectedAllergies((prev) =>
                          prev.includes(a)
                            ? prev.filter((x) => x !== a)
                            : [...prev, a],
                        )
                      }
                    />
                    <Label htmlFor={a} className="cursor-pointer">
                      {a}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">Cuisines to avoid?</h3>
              <Input
                pattern="[A-Za-z\s]+"
                placeholder="e.g. Spicy, Fast Food, Shellfish"
                value={excludedCuisines}
                onChange={(e) => setExcludedCuisines(e.target.value)}
              />
            </div>
          )}

          {errorMessage && (
            <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {errorMessage}
            </p>
          )}

          {timedOutGeneration && (
            <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              If this was a timeout, your backend generation may still complete
              shortly. You can close this wizard and click{" "}
              <span className="font-medium">Check for Completed Plan</span> on
              the dashboard.
            </p>
          )}

          <div className="flex justify-between mt-8 pt-4 border-t">
            <Button
              variant="ghost"
              onClick={step === 1 ? onCancel : handleBack}
              disabled={isSaving}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              {step === 1 ? "Cancel" : "Back"}
            </Button>

            <Button
              onClick={handleNext}
              disabled={!canProceed() || isSaving}
              className="bg-primary"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Loading...
                </>
              ) : (
                <>
                  {step === 5 ? "Finish & Generate" : "Next"}
                  <ChevronRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
