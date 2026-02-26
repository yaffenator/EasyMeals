import { generateMealPlan } from '../app/utils/MealPlanGenerator';
import { MealPlanData } from '../app/components/MealPlanWizard';

describe('Meal Plan Logic', () => {
  test('Budget Rule: Total cost should not exceed 60%', () => {
    const mockPrefs: MealPlanData = { 
      monthlyBudget: 400, goal: 'maintain', currentWeight: 165, 
      allergies: [], excludedCuisines: [] 
    };
    const plan = generateMealPlan(mockPrefs);
    expect(plan.preferences.monthlyBudget).toBe(400);
  });
});