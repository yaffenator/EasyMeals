from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from db.firestore_client import db


class PlanGenerationRequest(BaseModel):
    userId: str
    monthlyBudget: float
    goalType: str
    dietaryTags: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class GroceryListItem(BaseModel):
    ingredientId: str
    name: str
    totalQuantity: float
    unit: str


class PlanWeek(BaseModel):
    weekIndex: int
    meals: list[dict[str, Any]] = Field(default_factory=list)


class PlanGenerationResponse(BaseModel):
    userId: str
    planId: str
    status: str
    monthlyBudget: float
    estimatedTotalCost: float
    weeks: list[PlanWeek] = Field(default_factory=list)
    groceryList: list[GroceryListItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


TODO_FLOW = [
    "Generate validated meal plan from Gemini response schema.",
    "Upsert ingredient price entries and map ingredient ids.",
    "Recalculate all meal costs server-side.",
    "Deduplicate or create recipe documents.",
    "Apply diversity scoring to candidate meals.",
    "Enforce budget with lower-cost swaps when needed.",
    "Aggregate grocery list by ingredient and normalized unit.",
    "Persist users/{uid}/plans/{planId} and update mealHistory.",
]


def generate_and_store_plan(request: PlanGenerationRequest) -> PlanGenerationResponse:
    """
    Orchestrates plan creation and persistence for a user.

    Step 1 scaffold:
    - Define the stable function contract used by API routes.
    - Return a structured placeholder response until integration steps are implemented.
    """
    if db is None:
        raise ValueError("Firestore client is not initialized.")

    plan_id = f"plan_{uuid4().hex}"
    return PlanGenerationResponse(
        userId=request.userId,
        planId=plan_id,
        status="stub",
        monthlyBudget=request.monthlyBudget,
        estimatedTotalCost=0.0,
        weeks=[],
        groceryList=[],
        metadata={
            "implementedStep": 1,
            "todoFlow": TODO_FLOW,
        },
    )
