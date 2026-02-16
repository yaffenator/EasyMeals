import { MealPlanData } from '../components/MealPlanWizard';

export interface Recipe {
  id: string;
  day: string;
  name: string;
  description: string;
  image: string;
  prepTime: string;
  cost: string;
  servings: number;
  calories: number;
  category: string;
}

export interface WeeklyPlan {
  weekNumber: number;
  meals: Recipe[];
}

export interface FullMealPlan {
  preferences: MealPlanData;
  weeks: WeeklyPlan[];
  createdAt: string;
}

const mealTemplates = [
  {
    names: ['Creamy Chicken Pasta', 'Garlic Herb Chicken Pasta', 'Lemon Chicken Linguine', 'Pesto Chicken Pasta'],
    description: 'A delicious and budget-friendly pasta dish with tender chicken',
    image: 'https://images.unsplash.com/photo-1638890763825-e20495f6b819?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaGlja2VuJTIwcGFzdGElMjBkaXNofGVufDF8fHx8MTc3MDMxMzk3OHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '30 min',
    category: 'Dinner'
  },
  {
    names: ['Grilled Salmon with Vegetables', 'Baked Salmon with Asparagus', 'Pan-Seared Salmon Bowl', 'Honey Glazed Salmon'],
    description: 'Heart-healthy salmon paired with colorful vegetables',
    image: 'https://images.unsplash.com/photo-1633524792246-f25f5b0d66dc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxncmlsbGVkJTIwc2FsbW9uJTIwdmVnZXRhYmxlc3xlbnwxfHx8fDE3NzAyMjI4NTB8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '25 min',
    category: 'Dinner'
  },
  {
    names: ['Beef Stir Fry', 'Teriyaki Beef Bowl', 'Mongolian Beef', 'Ginger Beef Stir Fry'],
    description: 'Quick and easy Asian-inspired stir fry with tender beef',
    image: 'https://images.unsplash.com/photo-1768326119244-6b7055143e5f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxiZWVmJTIwc3RpciUyMGZyeSUyMHJpY2V8ZW58MXx8fHwxNzcwMzEzOTc5fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '20 min',
    category: 'Dinner'
  },
  {
    names: ['Vegetarian Burrito Bowl', 'Black Bean Rice Bowl', 'Mediterranean Grain Bowl', 'Quinoa Power Bowl'],
    description: 'Packed with protein and flavor, this bowl is a crowd pleaser',
    image: 'https://images.unsplash.com/photo-1647545401834-39096eb7e4ad?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx2ZWdldGFyaWFuJTIwYnVycml0byUyMGJvd2x8ZW58MXx8fHwxNzcwMzEzOTc5fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '25 min',
    category: 'Dinner'
  },
  {
    names: ['Turkey Meatballs in Marinara', 'Italian Turkey Meatballs', 'BBQ Turkey Meatballs', 'Asian-Style Turkey Meatballs'],
    description: 'Lean turkey meatballs in a rich savory sauce',
    image: 'https://images.unsplash.com/photo-1768187067375-4cd5a79fec41?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtZWF0YmFsbHMlMjB0b21hdG8lMjBzYXVjZXxlbnwxfHx8fDE3NzAzMTM5Nzl8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '35 min',
    category: 'Dinner'
  },
  {
    names: ['Shrimp Tacos with Fresh Salsa', 'Cajun Shrimp Tacos', 'Lime Cilantro Shrimp Tacos', 'Blackened Shrimp Tacos'],
    description: 'Light and zesty tacos perfect for any day',
    image: 'https://images.unsplash.com/photo-1719329468231-6e12eadd16a1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzaHJpbXAlMjB0YWNvcyUyMGZyZXNofGVufDF8fHx8MTc3MDMxMzk4MHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '20 min',
    category: 'Dinner'
  },
  {
    names: ['Chicken Curry with Rice', 'Thai Green Curry', 'Butter Chicken', 'Coconut Curry Chicken'],
    description: 'Aromatic curry with warming spices and tender chicken',
    image: 'https://images.unsplash.com/photo-1707448829764-9474458021ed?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaGlja2VuJTIwY3VycnklMjByaWNlfGVufDF8fHx8MTc3MDI1MTgzM3ww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    prepTime: '40 min',
    category: 'Dinner'
  }
];

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function calculateMealCost(baseCost: number, weeklyBudget: number): string {
  // Adjust cost based on weekly budget
  const adjustmentFactor = weeklyBudget / 60; // Base weekly budget of $60
  const adjustedCost = baseCost * adjustmentFactor;
  return `$${adjustedCost.toFixed(2)}`;
}

function calculateCalories(goal: 'lose' | 'gain' | 'maintain', baseCalories: number): number {
  switch (goal) {
    case 'lose':
      return Math.round(baseCalories * 0.85); // 15% fewer calories
    case 'gain':
      return Math.round(baseCalories * 1.20); // 20% more calories
    default:
      return baseCalories;
  }
}

export function generateMealPlan(data: MealPlanData): FullMealPlan {
  const weeklyBudget = data.monthlyBudget / 4;
  const weeks: WeeklyPlan[] = [];

  // Generate 4 weeks of meal plans
  for (let weekNum = 1; weekNum <= 4; weekNum++) {
    const meals: Recipe[] = [];

    days.forEach((day, dayIndex) => {
      // Select a template (cycle through them with some variation per week)
      const templateIndex = (dayIndex + weekNum) % mealTemplates.length;
      const template = mealTemplates[templateIndex];
      
      // Pick a name variant based on week
      const nameIndex = (weekNum - 1) % template.names.length;
      const mealName = template.names[nameIndex];

      // Base cost varies by meal type
      const baseCost = 6 + Math.random() * 5;
      const baseCalories = 400 + Math.floor(Math.random() * 200);

      meals.push({
        id: `week${weekNum}-day${dayIndex + 1}`,
        day,
        name: mealName,
        description: template.description,
        image: template.image,
        prepTime: template.prepTime,
        cost: calculateMealCost(baseCost, weeklyBudget),
        servings: 4,
        calories: calculateCalories(data.goal, baseCalories),
        category: template.category
      });
    });

    weeks.push({
      weekNumber: weekNum,
      meals
    });
  }

  return {
    preferences: data,
    weeks,
    createdAt: new Date().toISOString()
  };
}

export function saveMealPlan(mealPlan: FullMealPlan): void {
  localStorage.setItem('mealPlan', JSON.stringify(mealPlan));
}

export function loadMealPlan(): FullMealPlan | null {
  const stored = localStorage.getItem('mealPlan');
  return stored ? JSON.parse(stored) : null;
}

export function clearMealPlan(): void {
  localStorage.removeItem('mealPlan');
}
