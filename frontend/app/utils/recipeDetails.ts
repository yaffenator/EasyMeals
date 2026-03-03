import { Recipe } from './MealPlanGenerator';

export interface DetailedRecipe extends Recipe {
  protein: string;
  carbs: string;
  fat: string;
  difficulty: string;
  ingredients: string[];
  instructions: string[];
  tips: string[];
  nutritionInfo?: {
    calories: string;
    protein: string;
    carbs: string;
    fat: string;
  };
  costPerServing: string;
  cookTime: number;
}

// Generate detailed recipe information based on the base recipe
export function generateRecipeDetails(recipe: Recipe): DetailedRecipe {
  
  // Calculate cost per serving
  const totalCost = parseFloat(String(recipe.totalCost).replace('$', ''));
  const costPerServing = (totalCost / recipe.servings).toFixed(2);

  return {
    ...recipe,
    protein: recipe.protein,
    carbs: recipe.carbs,
    fat: recipe.fat,
    difficulty: recipe.difficulty,
    ingredients: recipe.ingredients,
    instructions: recipe.instructions,
    tips: recipe.tips,
    nutritionInfo: {
      calories: `${recipe.calories}`,
      protein: recipe.protein,
      carbs: recipe.carbs,
      fat: recipe.fat
    },
    costPerServing,
    cookTime: recipe.cookTime
  };
}
