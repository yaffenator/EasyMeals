import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import Dashboard from "../page";

const mockPush = jest.fn();
const mockSetMealPlan = jest.fn();
const mockUseMealPlan = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("../../context/auth", () => ({
  useAuth: jest.fn().mockReturnValue({
    currentUser: { displayName: "Test User", email: "test@test.com" },
  }),
}));

jest.mock("../../firebase", () => ({
  auth: {
    currentUser: {
      uid: "user_1",
      displayName: "Test User",
      email: "test@test.com",
    },
  },
  db: {},
}));

jest.mock("firebase/firestore", () => ({
  doc: jest.fn(),
  getDoc: jest.fn().mockResolvedValue({
    exists: () => true,
    data: () => ({ mealPlanProfile: { questionnaireCompleted: true } }),
  }),
}));

jest.mock("../../context/MealPlanContext", () => ({
  useMealPlan: () => mockUseMealPlan(),
}));

describe("Dashboard Page", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockSetMealPlan.mockClear();
  });

  it('shows create-plan prompt when no plan exists', async () => {
    mockUseMealPlan.mockReturnValue({
      mealPlan: null,
      setMealPlan: mockSetMealPlan,
      isLoading: false,
      error: null,
      refreshPlan: jest.fn(),
    });

    render(<Dashboard />);

    expect(await screen.findByText("Welcome, Test User!")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create Your Meal Plan/i })).toBeInTheDocument();
  });

  it("shows current meal plan details when plan exists", async () => {
    mockUseMealPlan.mockReturnValue({
      mealPlan: {
        preferences: { monthlyBudget: 500 },
        weeks: [
          {
            weekNumber: 1,
            meals: [
              {
                id: "1",
                day: "Monday",
                name: "Test Meal",
                description: "A test meal",
                image: "https://example.com/image.jpg",
                prepTime: "30 min",
                totalCost: "$10.00",
                costPerServing: 10,
                calories: 500,
              },
            ],
          },
        ],
      },
      setMealPlan: mockSetMealPlan,
      isLoading: false,
      error: null,
      refreshPlan: jest.fn(),
    });

    render(<Dashboard />);

    expect(await screen.findByText("Select Week")).toBeInTheDocument();
    expect(screen.getByText("Weekly Cost")).toBeInTheDocument();
    expect(screen.getByText("Avg. Prep Time")).toBeInTheDocument();
    expect(screen.getByText("Test Meal")).toBeInTheDocument();
  });

  it('opens wizard when "Generate New Plan" is clicked', async () => {
    mockUseMealPlan.mockReturnValue({
      mealPlan: {
        preferences: { monthlyBudget: 500 },
        weeks: [{ weekNumber: 1, meals: [] }],
      },
      setMealPlan: mockSetMealPlan,
      isLoading: false,
      error: null,
      refreshPlan: jest.fn(),
    });

    render(<Dashboard />);
    await screen.findByText("Select Week");
    fireEvent.click(screen.getByRole("button", { name: /Generate New Plan/i }));

    expect(mockSetMealPlan).toHaveBeenCalledWith(null);
  });
});
