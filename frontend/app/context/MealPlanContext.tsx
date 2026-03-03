"use client";
import React, { createContext, useContext, useState, useEffect, useRef } from "react";
import { auth, uploadMealPlanToUser, loadMealPlanFromFirestore } from "../firebase";

const MealPlanContext = createContext<any>(null);

export function MealPlanProvider({ children }: { children: React.ReactNode }) {
  const [mealPlan, setMealPlan] = useState<any>(null);
  const processingMeals = useRef(new Set());

  // Load plan on auth change
  useEffect(() => {
    const unsub = auth.onAuthStateChanged(async (user) => {
      if (user) {
        const plan = await loadMealPlanFromFirestore(user.uid);
        setMealPlan(plan);
      }
    });
    return unsub;
  }, []);

  // BACKGROUND WORKER
  useEffect(() => {
    const hydrate = async () => {
      if (!mealPlan || !auth.currentUser) return;

      const allPending = mealPlan.weeks
        .flatMap((w: any) => w.meals)
        .filter((m: any) => m.status === "pending");

      for (const meal of allPending) {
        if (processingMeals.current.has(meal.id)) continue;
        processingMeals.current.add(meal.id);

        try {
          const res = await fetch("/api/generate-recipe", {
            method: "POST",
            body: JSON.stringify({ mealName: meal.name, preferences: mealPlan.preferences }),
          });
          const fullData = await res.json();

          setMealPlan((prev: any) => {
            const updatedWeeks = prev.weeks.map((w: any) => ({
              ...w,
              meals: w.meals.map((m: any) => 
                m.id === meal.id ? { ...m, ...fullData, status: "completed" } : m
              ),
            }));
            const newPlan = { ...prev, weeks: updatedWeeks };
            // Save to Firebase immediately
            uploadMealPlanToUser(auth.currentUser!.uid, newPlan);
            return newPlan;
          });
        } catch (e) {
          processingMeals.current.delete(meal.id);
        }
      }
    };
    hydrate();
  }, [mealPlan?.weeks, mealPlan?.preferences]); // Watches for new skeletons

  return (
    <MealPlanContext.Provider value={{ mealPlan, setMealPlan }}>
      {children}
    </MealPlanContext.Provider>
  );
}

export const useMealPlan = () => useContext(MealPlanContext);