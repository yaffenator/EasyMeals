"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

import { auth } from "../firebase";

type MealLike = Record<string, unknown> & {
  costPerServing?: number | string;
};

type PlanWeek = {
  weekIndex?: number;
  weekNumber?: number;
  meals: MealLike[];
};

export type MealPlan = {
  userId?: string;
  planId?: string;
  status?: string;
  monthlyBudget?: number;
  estimatedTotalCost?: number;
  groceryList?: unknown[];
  metadata?: Record<string, unknown>;
  weeks: PlanWeek[];
  preferences?: Record<string, unknown>;
  createdAt?: string;
};

type MealPlanContextValue = {
  mealPlan: MealPlan | null;
  setMealPlan: React.Dispatch<React.SetStateAction<MealPlan | null>>;
  isLoading: boolean;
  error: string | null;
  refreshPlan: () => Promise<void>;
};

const MealPlanContext = createContext<MealPlanContextValue | null>(null);

function toNumber(value: unknown, fallback: number = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value.replace("$", "").trim());
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function normalizePlan(raw: unknown): MealPlan | null {
  if (!raw || typeof raw !== "object") return null;
  const wrapper = raw as Record<string, unknown>;
  const nestedPlan =
    wrapper.plan && typeof wrapper.plan === "object"
      ? (wrapper.plan as Record<string, unknown>)
      : wrapper;

  const rawWeeks = Array.isArray(nestedPlan.weeks) ? nestedPlan.weeks : [];

  const normalizedWeeks: PlanWeek[] = rawWeeks.map((week, weekIdx) => {
    const weekObj = (week ?? {}) as Record<string, unknown>;
    const meals = Array.isArray(weekObj.meals) ? weekObj.meals : [];

    const normalizedMeals: MealLike[] = meals.map((meal, mealIdx) => {
      const mealObj = (meal ?? {}) as Record<string, unknown>;
      const costPerServing = toNumber(mealObj.costPerServing, 0);

      return {
        ...mealObj,
        day:
          typeof mealObj.day === "string"
            ? mealObj.day
            : ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][mealIdx % 7],
        totalCost:
          typeof mealObj.totalCost === "string"
            ? mealObj.totalCost
            : `$${costPerServing.toFixed(2)}`,
        costPerServing,
      };
    });

    const weekIndex = typeof weekObj.weekIndex === "number" ? weekObj.weekIndex : weekIdx;
    return {
      ...weekObj,
      weekIndex,
      weekNumber: weekIndex + 1,
      meals: normalizedMeals,
    };
  });

  return {
    userId: typeof wrapper.userId === "string" ? wrapper.userId : undefined,
    planId: typeof wrapper.planId === "string" ? wrapper.planId : undefined,
    status: typeof nestedPlan.status === "string" ? nestedPlan.status : undefined,
    monthlyBudget: toNumber(nestedPlan.monthlyBudget, 0),
    estimatedTotalCost: toNumber(nestedPlan.estimatedTotalCost, 0),
    groceryList: Array.isArray(nestedPlan.groceryList) ? nestedPlan.groceryList : [],
    metadata:
      nestedPlan.metadata && typeof nestedPlan.metadata === "object"
        ? (nestedPlan.metadata as Record<string, unknown>)
        : undefined,
    weeks: normalizedWeeks,
    preferences:
      nestedPlan.preferences && typeof nestedPlan.preferences === "object"
        ? (nestedPlan.preferences as Record<string, unknown>)
        : undefined,
    createdAt: typeof nestedPlan.createdAt === "string" ? nestedPlan.createdAt : undefined,
  };
}

export function MealPlanProvider({ children }: { children: React.ReactNode }) {
  const [mealPlan, setMealPlan] = useState<MealPlan | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLatestPlan = useCallback(async () => {
    const uid = auth.currentUser?.uid;
    if (!uid) {
      setMealPlan(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/plan/latest?userId=${encodeURIComponent(uid)}`, {
        method: "GET",
        cache: "no-store",
      });

      if (response.status === 404) {
        setMealPlan(null);
        return;
      }

      const payload = await response.json();
      if (!response.ok) {
        const detail =
          payload && typeof payload === "object" && "detail" in payload ? String(payload.detail) : "Failed to load plan";
        throw new Error(detail);
      }

      setMealPlan(normalizePlan(payload));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load plan";
      setError(message);
      setMealPlan(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async () => {
      await fetchLatestPlan();
    });
    return unsubscribe;
  }, [fetchLatestPlan]);

  return (
    <MealPlanContext.Provider
      value={{
        mealPlan,
        setMealPlan,
        isLoading,
        error,
        refreshPlan: fetchLatestPlan,
      }}
    >
      {children}
    </MealPlanContext.Provider>
  );
}

export const useMealPlan = () => {
  const ctx = useContext(MealPlanContext);
  if (!ctx) {
    throw new Error("useMealPlan must be used within MealPlanProvider");
  }
  return ctx;
};
