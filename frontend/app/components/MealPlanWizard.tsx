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
import { ChevronRight, ChevronLeft, Plus, X, Loader2 } from "lucide-react";
import { updateUserPreferences, uploadMealPlanToUser } from "../firebase";
import { auth } from "../firebase";

interface MealPlanWizardProps {
  onComplete: (data: MealPlanData) => void;
  onCancel: () => void;
}

export interface MealPlanData {
  monthlyBudget: number;
  goal: "lose" | "gain" | "maintain";
  currentWeight: number;
  allergies: string[];
  excludedCuisines: string[];
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
  const [loading, setLoading] = useState(false);

  // Form State
  const [monthlyBudget, setMonthlyBudget] = useState("");
  const [goal, setGoal] = useState<"lose" | "gain" | "maintain">("maintain");
  const [weight, setWeight] = useState("");
  const [selectedAllergies, setSelectedAllergies] = useState<string[]>([]);
  const [otherAllergyChecked, setOtherAllergyChecked] = useState(false);
  const [customAllergies, setCustomAllergies] = useState<string[]>([""]);
  const [excludedCuisines, setExcludedCuisines] = useState("");

  const handleNext = async () => {
    if (step < 5) {
      setStep(step + 1);
    } else {
      setIsSaving(true);

      // --- THIS IS WHERE WE DEFINE finalData ---
      const finalData = {
        questionnaireCompleted: true,
        monthlyBudget: parseFloat(monthlyBudget),
        goal: goal,
        currentWeight: parseFloat(weight),
        allergies: selectedAllergies,
        excludedCuisines: excludedCuisines
          .split(",")
          .map((c) => c.trim())
          .filter((c) => c !== ""),
      };

      try {
        const uid = auth.currentUser?.uid; // Safely get the user's ID
        if (uid) {
          await updateUserPreferences(uid, finalData);
        }
      } catch (error) {
        console.error("Failed to save to database:", error);
        // Optional: show an error toast/message to the user
      }

      try {
        const response = await fetch("/api/save-preferences", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(finalData), // Now the computer knows what finalData is
        });

        if (!response.ok) throw new Error("Generation failed");

        const fullMealPlan = await response.json();

        const uid = auth.currentUser?.uid;
        if (uid && fullMealPlan.mealPlan) {
          await uploadMealPlanToUser(uid, fullMealPlan.mealPlan);
        }

        onComplete(fullMealPlan);
      } catch (error) {
        console.error("Error:", error);
        alert("Something went wrong. Check your console!");
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleBack = () => step > 1 && setStep(step - 1);

  const canProceed = () => {
    if (step === 1)
      return monthlyBudget !== "" && parseFloat(monthlyBudget) > 0;
    if (step === 2) return !!goal;
    if (step === 3) return weight !== "" && parseFloat(weight) > 0;
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
          {/* STEP 1: BUDGET */}
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
                  placeholder="400"
                  value={monthlyBudget}
                  onChange={(e) => setMonthlyBudget(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* STEP 2: GOAL */}
          {step === 2 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">
                What is your primary goal?
              </h3>
              <RadioGroup
                value={goal}
                onValueChange={(v: any) => setGoal(v)}
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

          {/* STEP 3: WEIGHT */}
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
                  placeholder="165"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* STEP 4: ALLERGIES */}
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

          {/* STEP 5: CUISINES */}
          {step === 5 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium">Cuisines to avoid?</h3>
              <Input
                placeholder="e.g. Spicy, Fast Food, Shellfish"
                value={excludedCuisines}
                onChange={(e) => setExcludedCuisines(e.target.value)}
              />
            </div>
          )}

          {/* NAVIGATION */}
          <div className="flex justify-between mt-8 pt-4 border-t">
            <Button
              variant="ghost"
              onClick={step === 1 ? onCancel : handleBack}
              disabled={isSaving}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />{" "}
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
                  {step === 5 ? "Finish & Generate" : "Next"}{" "}
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
