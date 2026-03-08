"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

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
  refreshPlan: (options?: { silent?: boolean }) => Promise<MealPlan | null>;
  lastRefreshAt: number;
  imageSyncStatus: "idle" | "syncing" | "ready" | "timeout";
};

const MealPlanContext = createContext<MealPlanContextValue | null>(null);
const PLAN_POLL_INTERVAL_MS = 8_000;
const PLAN_POLL_MAX_DURATION_MS = 8 * 60_000;
const IMAGE_POLL_INTERVAL_MS = 10_000;
const IMAGE_POLL_MAX_DURATION_MS = 5 * 60_000;

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
        status:
          typeof mealObj.status === "string"
            ? mealObj.status
            : typeof nestedPlan.status === "string" && nestedPlan.status.toLowerCase() === "ready"
              ? "completed"
              : "pending",
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

function hasPendingImages(plan: MealPlan | null): boolean {
  if (!plan) return false;
  for (const week of plan.weeks) {
    for (const meal of week.meals) {
      const imageValue = typeof meal.image === "string" ? meal.image.trim() : "";
      const status = typeof meal.imageGenStatus === "string" ? meal.imageGenStatus.toLowerCase() : "";
      const missingImage =
        !imageValue || imageValue.startsWith("/api/placeholder") || imageValue.startsWith("/meal-placeholder");
      if (status === "pending" || (missingImage && status !== "failed")) {
        return true;
      }
    }
  }
  return false;
}

function hasPendingMealDetails(plan: MealPlan | null): boolean {
  if (!plan) return false;
  const planStatus = typeof plan.status === "string" ? plan.status.toLowerCase() : "";
  if (planStatus === "generating") return true;
  for (const week of plan.weeks) {
    for (const meal of week.meals) {
      const status = typeof meal.status === "string" ? meal.status.toLowerCase() : "";
      if (!status || status === "pending") {
        return true;
      }
    }
  }
  return false;
}

function hasCompletedMeals(plan: MealPlan | null): boolean {
  if (!plan) return false;
  for (const week of plan.weeks) {
    for (const meal of week.meals) {
      const status = typeof meal.status === "string" ? meal.status.toLowerCase() : "";
      if (status === "completed") {
        return true;
      }
    }
  }
  return false;
}

export function MealPlanProvider({ children }: { children: React.ReactNode }) {
  const [mealPlan, setMealPlan] = useState<MealPlan | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<number>(Date.now());
  const [imageSyncStatus, setImageSyncStatus] = useState<"idle" | "syncing" | "ready" | "timeout">("idle");
  const imageTriggerByPlan = useRef<Set<string>>(new Set());
  const imagePollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const imagePollStartedAtRef = useRef<number | null>(null);
  const imageReadyNoticeShownRef = useRef<Set<string>>(new Set());
  const planPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const planPollStartedAtRef = useRef<number | null>(null);

  const fetchLatestPlan = useCallback(async (options?: { silent?: boolean }) => {
    const silent = Boolean(options?.silent);
    const user = auth.currentUser;
    if (!user?.uid) {
      setMealPlan(null);
      setIsLoading(false);
      return null;
    }
    const uid = user.uid;

    if (!silent) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const idToken = await user.getIdToken();
      const response = await fetch(`/api/plan/latest?userId=${encodeURIComponent(uid)}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
        cache: "no-store",
      });

      if (response.status === 404) {
        setMealPlan(null);
        return null;
      }

      const payload = await response.json();
      if (!response.ok) {
        const detail =
          payload && typeof payload === "object" && "detail" in payload ? String(payload.detail) : "Failed to load plan";
        throw new Error(detail);
      }

      const normalized = normalizePlan(payload);
      setMealPlan(normalized);
      setLastRefreshAt(Date.now());
      return normalized;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load plan";
      setError(message);
      setMealPlan(null);
      return null;
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async () => {
      await fetchLatestPlan();
    });
    return unsubscribe;
  }, [fetchLatestPlan]);

  useEffect(() => {
    if (!mealPlan) return;
    const uid = auth.currentUser?.uid;
    if (!uid) return;

    const planKey = mealPlan.planId || `anon-${mealPlan.createdAt || "unknown"}`;
    if (imageTriggerByPlan.current.has(planKey)) return;
    if (!hasCompletedMeals(mealPlan)) return;

    const hasMissingImage = mealPlan.weeks.some((week) =>
      week.meals.some((meal) => {
        const src = typeof meal.image === "string" ? meal.image.trim() : "";
        return !src || src.startsWith("/api/placeholder") || src.startsWith("/meal-placeholder");
      }),
    );

    if (!hasMissingImage) return;
    imageTriggerByPlan.current.add(planKey);

    fetch("/api/generate-meal-images", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid }),
    }).catch((err) => {
      console.error("Failed to trigger image generation job:", err);
    });
  }, [mealPlan]);

  useEffect(() => {
    if (!mealPlan) {
      if (planPollIntervalRef.current) {
        clearInterval(planPollIntervalRef.current);
        planPollIntervalRef.current = null;
      }
      planPollStartedAtRef.current = null;
      return;
    }

    if (!hasPendingMealDetails(mealPlan)) {
      if (planPollIntervalRef.current) {
        clearInterval(planPollIntervalRef.current);
        planPollIntervalRef.current = null;
      }
      planPollStartedAtRef.current = null;
      return;
    }

    if (planPollIntervalRef.current) return;

    planPollStartedAtRef.current = Date.now();
    planPollIntervalRef.current = setInterval(async () => {
      const startedAt = planPollStartedAtRef.current ?? Date.now();
      if (Date.now() - startedAt > PLAN_POLL_MAX_DURATION_MS) {
        if (planPollIntervalRef.current) {
          clearInterval(planPollIntervalRef.current);
          planPollIntervalRef.current = null;
        }
        return;
      }

      const latest = await fetchLatestPlan({ silent: true });
      if (!hasPendingMealDetails(latest)) {
        if (planPollIntervalRef.current) {
          clearInterval(planPollIntervalRef.current);
          planPollIntervalRef.current = null;
        }
      }
    }, PLAN_POLL_INTERVAL_MS);

    return () => {
      if (planPollIntervalRef.current) {
        clearInterval(planPollIntervalRef.current);
        planPollIntervalRef.current = null;
      }
    };
  }, [mealPlan, fetchLatestPlan]);

  useEffect(() => {
    if (!mealPlan) {
      setImageSyncStatus("idle");
      if (imagePollIntervalRef.current) {
        clearInterval(imagePollIntervalRef.current);
        imagePollIntervalRef.current = null;
      }
      imagePollStartedAtRef.current = null;
      return;
    }
    if (!hasCompletedMeals(mealPlan)) {
      setImageSyncStatus("idle");
      if (imagePollIntervalRef.current) {
        clearInterval(imagePollIntervalRef.current);
        imagePollIntervalRef.current = null;
      }
      imagePollStartedAtRef.current = null;
      return;
    }

    const planKey = mealPlan.planId || `anon-${mealPlan.createdAt || "unknown"}`;
    const pending = hasPendingImages(mealPlan);

    if (!pending) {
      if (!imageReadyNoticeShownRef.current.has(planKey)) {
        setImageSyncStatus("ready");
        imageReadyNoticeShownRef.current.add(planKey);
      } else if (imageSyncStatus !== "ready") {
        setImageSyncStatus("idle");
      }
      if (imagePollIntervalRef.current) {
        clearInterval(imagePollIntervalRef.current);
        imagePollIntervalRef.current = null;
      }
      imagePollStartedAtRef.current = null;
      return;
    }

    setImageSyncStatus("syncing");
    if (imagePollIntervalRef.current) return;

    imagePollStartedAtRef.current = Date.now();
    imagePollIntervalRef.current = setInterval(async () => {
      const startedAt = imagePollStartedAtRef.current ?? Date.now();
      if (Date.now() - startedAt > IMAGE_POLL_MAX_DURATION_MS) {
        setImageSyncStatus("timeout");
        if (imagePollIntervalRef.current) {
          clearInterval(imagePollIntervalRef.current);
          imagePollIntervalRef.current = null;
        }
        return;
      }

      const latest = await fetchLatestPlan({ silent: true });
      if (!hasPendingImages(latest)) {
        setImageSyncStatus("ready");
        const latestKey = latest?.planId || planKey;
        imageReadyNoticeShownRef.current.add(latestKey);
        if (imagePollIntervalRef.current) {
          clearInterval(imagePollIntervalRef.current);
          imagePollIntervalRef.current = null;
        }
      }
    }, IMAGE_POLL_INTERVAL_MS);

    return () => {
      if (imagePollIntervalRef.current) {
        clearInterval(imagePollIntervalRef.current);
        imagePollIntervalRef.current = null;
      }
    };
  }, [mealPlan, fetchLatestPlan, imageSyncStatus]);

  return (
    <MealPlanContext.Provider
      value={{
        mealPlan,
        setMealPlan,
        isLoading,
        error,
        refreshPlan: fetchLatestPlan,
        lastRefreshAt,
        imageSyncStatus,
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
