import { Recipe } from './MealPlanGenerator';

export interface DetailedRecipe extends Partial<Recipe> {
  name: string;
  day: string;
  description: string;
  image: string;
  prepTime: string;
  servings: number;
  calories: number;
  protein: string;
  carbs: string;
  fat: string;
  difficulty: string;
  ingredients: string[];
  instructions: string[];
  tips: string[];
  totalCost: string;
  costPerServing: string;
  cookTime: number;
  nutritionInfo?: {
    calories: string;
    protein: string;
    carbs: string;
    fat: string;
  };
}

type RecipeLike = Partial<Recipe> & {
  totalCost?: string | number;
  cost?: string | number;
  protein?: string | number;
  carbs?: string | number;
  fat?: string | number;
  difficulty?: string;
  ingredients?: string[];
  instructions?: string[];
  tips?: string[];
  cookTime?: number;
};

function toMoneyString(value: string | number | undefined): string {
  if (typeof value === 'number') return `$${value.toFixed(2)}`;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return '$0.00';
    return trimmed.startsWith('$') ? trimmed : `$${trimmed}`;
  }
  return '$0.00';
}

export function generateRecipeDetails(input: RecipeLike): DetailedRecipe {
  const servings = typeof input.servings === 'number' && input.servings > 0 ? input.servings : 1;
  const totalCost = toMoneyString(input.totalCost ?? input.cost);
  const numericTotal = Number.parseFloat(totalCost.replace('$', '')) || 0;
  const costPerServing = `$${(numericTotal / servings).toFixed(2)}`;

  const protein = input.protein != null ? String(input.protein) : '0g';
  const carbs = input.carbs != null ? String(input.carbs) : '0g';
  const fat = input.fat != null ? String(input.fat) : '0g';

  return {
    ...input,
    name: input.name ? String(input.name) : 'Recipe',
    day: input.day ? String(input.day) : 'Day',
    description: input.description ? String(input.description) : '',
    image: input.image ? String(input.image) : '/api/placeholder/400/300',
    prepTime: input.prepTime ? String(input.prepTime) : '0 min',
    servings,
    calories: typeof input.calories === 'number' ? input.calories : 0,
    protein,
    carbs,
    fat,
    difficulty: input.difficulty ? String(input.difficulty) : 'Medium',
    ingredients: Array.isArray(input.ingredients) ? input.ingredients : [],
    instructions: Array.isArray(input.instructions) ? input.instructions : [],
    tips: Array.isArray(input.tips) ? input.tips : [],
    totalCost,
    costPerServing,
    cookTime: typeof input.cookTime === 'number' ? input.cookTime : 0,
    nutritionInfo: {
      calories: `${typeof input.calories === 'number' ? input.calories : 0}`,
      protein,
      carbs,
      fat,
    },
  };
}
