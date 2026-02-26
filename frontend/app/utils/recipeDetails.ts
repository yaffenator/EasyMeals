import { Recipe, loadMealPlan } from './MealPlanGenerator';

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

// Get recipe details by ID
export function getRecipeDetails(recipeId: string): DetailedRecipe | null {
  const mealPlan = loadMealPlan();
  if (!mealPlan) return null;

  // Find the recipe in all weeks
  for (const week of mealPlan.weeks) {
    const recipe = week.meals.find(meal => meal.id === recipeId);
    if (recipe) {
      return generateRecipeDetails(recipe);
    }
  }

  return null;
}

// Generate detailed recipe information based on the base recipe
export function generateRecipeDetails(recipe: Recipe): DetailedRecipe {
  const baseCalories = recipe.calories;
  
  // Calculate macros based on calories (rough estimates)
  const protein = Math.round(baseCalories * 0.25 / 4); // 25% of calories from protein
  const carbs = Math.round(baseCalories * 0.45 / 4); // 45% of calories from carbs
  const fat = Math.round(baseCalories * 0.30 / 9); // 30% of calories from fat

  // Determine difficulty based on prep time
  const prepMinutes = parseInt(recipe.prepTime);
  let difficulty = 'Easy';
  if (prepMinutes > 35) difficulty = 'Hard';
  else if (prepMinutes > 25) difficulty = 'Medium';

  // Generate ingredients based on meal type
  const ingredients = generateIngredients(recipe.name);
  
  // Generate instructions
  const instructions = generateInstructions(recipe.name, ingredients);
  
  // Generate tips
  const tips = generateTips(recipe.name);

  // Calculate cost per serving
  const totalCost = parseFloat(recipe.cost.replace('$', ''));
  const costPerServing = (totalCost / recipe.servings).toFixed(2);

  // Estimate cook time (usually slightly longer than prep time)
  const cookTime = prepMinutes + Math.round(prepMinutes * 0.5);

  return {
    ...recipe,
    protein: `${protein}g`,
    carbs: `${carbs}g`,
    fat: `${fat}g`,
    difficulty,
    ingredients,
    instructions,
    tips,
    nutritionInfo: {
      calories: `${recipe.calories}`,
      protein: `${protein}g`,
      carbs: `${carbs}g`,
      fat: `${fat}g`
    },
    costPerServing,
    cookTime
  };
}

function generateIngredients(mealName: string): string[] {
  const lowerName = mealName.toLowerCase();

  // Chicken pasta dishes
  if (lowerName.includes('chicken') && lowerName.includes('pasta')) {
    return [
      '12 oz pasta (penne or linguine)',
      '1 lb chicken breast, diced',
      '2 cups cream or milk',
      '1 cup parmesan cheese, grated',
      '3 cloves garlic, minced',
      '2 tbsp olive oil',
      '1 cup spinach or vegetables',
      'Salt and pepper to taste',
      'Fresh herbs for garnish'
    ];
  }

  // Salmon dishes
  if (lowerName.includes('salmon')) {
    return [
      '4 salmon fillets (6 oz each)',
      '2 cups broccoli florets',
      '2 bell peppers, sliced',
      '1 zucchini, sliced',
      '3 tbsp olive oil',
      '2 cloves garlic, minced',
      'Lemon juice and zest',
      'Fresh herbs (dill or parsley)',
      'Salt and pepper to taste'
    ];
  }

  // Beef stir fry
  if (lowerName.includes('beef') && (lowerName.includes('stir') || lowerName.includes('bowl'))) {
    return [
      '1 lb beef sirloin, thinly sliced',
      '3 cups cooked rice',
      '2 cups mixed vegetables',
      '3 tbsp soy sauce',
      '2 tbsp oyster or teriyaki sauce',
      '1 tbsp sesame oil',
      '2 cloves garlic, minced',
      '1 tbsp ginger, grated',
      '2 tbsp vegetable oil',
      'Green onions and sesame seeds for garnish'
    ];
  }

  // Vegetarian bowls
  if (lowerName.includes('bowl') || lowerName.includes('burrito')) {
    return [
      '2 cups cooked rice or quinoa',
      '1 can (15 oz) black beans, drained',
      '1 cup corn kernels',
      '1 bell pepper, diced',
      '1 avocado, sliced',
      '1 cup cherry tomatoes, halved',
      '1/2 cup shredded cheese',
      'Lime juice',
      'Fresh cilantro',
      'Sour cream or Greek yogurt',
      'Salt, pepper, and cumin to taste'
    ];
  }

  // Meatballs
  if (lowerName.includes('meatball')) {
    return [
      '1 lb ground turkey or beef',
      '1/2 cup breadcrumbs',
      '1 egg',
      '1/4 cup parmesan cheese',
      '2 cloves garlic, minced',
      '2 cups marinara or BBQ sauce',
      '1 tbsp Italian seasoning',
      'Salt and pepper to taste',
      'Fresh basil for garnish',
      'Cooked pasta or rice for serving'
    ];
  }

  // Tacos
  if (lowerName.includes('taco')) {
    return [
      '1 lb shrimp, peeled and deveined',
      '8 small tortillas',
      '2 cups shredded cabbage',
      '1 cup cherry tomatoes, diced',
      '1 avocado, sliced',
      '1/4 cup sour cream or mayo',
      'Lime juice',
      '2 tsp chili powder',
      'Fresh cilantro',
      'Salt and pepper to taste'
    ];
  }

  // Curry dishes
  if (lowerName.includes('curry')) {
    return [
      '1 lb chicken, cubed',
      '1 can (14 oz) coconut milk',
      '2 tbsp curry paste or powder',
      '1 onion, diced',
      '2 cloves garlic, minced',
      '1 tbsp ginger, grated',
      '2 cups vegetables (bell peppers, carrots)',
      '3 cups cooked basmati rice',
      '2 tbsp oil',
      'Fresh cilantro',
      'Salt to taste'
    ];
  }

  // Default ingredients
  return [
    'Main protein (1 lb)',
    'Vegetables (2-3 cups)',
    'Aromatics (garlic, onion)',
    'Oil or butter (2-3 tbsp)',
    'Seasonings and spices',
    'Fresh herbs',
    'Salt and pepper to taste'
  ];
}

function generateInstructions(mealName: string, ingredients: string[]): string[] {
  const lowerName = mealName.toLowerCase();

  if (lowerName.includes('pasta')) {
    return [
      'Cook pasta according to package directions. Drain and set aside.',
      'Heat oil in a large skillet over medium-high heat. Season protein with salt and pepper.',
      'Cook protein until golden brown and cooked through, about 6-8 minutes. Remove from skillet.',
      'In the same skillet, add aromatics and cook until fragrant, about 1 minute.',
      'Add cream or sauce and bring to a simmer. Cook for 3-4 minutes until slightly thickened.',
      'Stir in cheese until melted and smooth.',
      'Add any vegetables and cook until wilted or tender.',
      'Return protein to the skillet along with cooked pasta. Toss to combine.',
      'Season with additional salt and pepper if needed.',
      'Garnish with fresh herbs and serve hot.'
    ];
  }

  if (lowerName.includes('salmon') || lowerName.includes('fish')) {
    return [
      'Preheat oven to 425°F (220°C).',
      'Toss vegetables with oil, salt, and pepper. Spread on a baking sheet.',
      'Roast vegetables for 15 minutes.',
      'Meanwhile, season fish with salt, pepper, and aromatics.',
      'Heat oil in an oven-safe skillet over medium-high heat.',
      'Sear fish for 3-4 minutes until golden on one side.',
      'Flip fish and transfer skillet to oven with the vegetables.',
      'Bake for 8-10 minutes until fish is cooked through and flakes easily.',
      'Squeeze fresh citrus juice over fish and garnish with herbs.',
      'Serve immediately with roasted vegetables.'
    ];
  }

  if (lowerName.includes('stir fry') || (lowerName.includes('beef') && lowerName.includes('bowl'))) {
    return [
      'Prepare rice according to package directions if not already cooked.',
      'Mix sauce ingredients in a small bowl and set aside.',
      'Heat oil in a large wok or skillet over high heat.',
      'Add protein in a single layer and cook without stirring for 2 minutes.',
      'Stir and continue cooking until browned. Remove and set aside.',
      'Add vegetables and stir-fry for 3-4 minutes until crisp-tender.',
      'Add aromatics and cook for 30 seconds until fragrant.',
      'Return protein to the wok and pour in the sauce.',
      'Toss everything together for 1-2 minutes until well coated.',
      'Serve over rice with garnishes.'
    ];
  }

  if (lowerName.includes('bowl') || lowerName.includes('burrito')) {
    return [
      'Cook rice or grains according to package directions.',
      'Heat beans in a small pot with seasonings until warm.',
      'Prepare all vegetables by dicing, slicing, or chopping as needed.',
      'If using, cook any protein with oil and seasonings until done.',
      'Divide rice among serving bowls.',
      'Top each bowl with beans, vegetables, and protein.',
      'Add fresh toppings like avocado, cheese, and herbs.',
      'Drizzle with dressing or add sour cream.',
      'Squeeze fresh lime juice over each bowl.',
      'Serve immediately and enjoy!'
    ];
  }

  if (lowerName.includes('meatball')) {
    return [
      'Preheat oven to 400°F (200°C) and line a baking sheet with parchment paper.',
      'In a large bowl, combine ground meat, breadcrumbs, egg, cheese, and seasonings.',
      'Mix gently until just combined - don\'t overmix.',
      'Form mixture into 1.5-inch meatballs and place on prepared baking sheet.',
      'Bake for 15-20 minutes until cooked through and browned.',
      'While meatballs bake, heat sauce in a large skillet.',
      'Add cooked meatballs to the sauce and simmer for 5-10 minutes.',
      'Cook pasta or rice according to package directions.',
      'Serve meatballs and sauce over pasta or rice.',
      'Garnish with fresh herbs and grated cheese.'
    ];
  }

  if (lowerName.includes('taco')) {
    return [
      'Season protein with spices, salt, and pepper.',
      'Heat oil in a skillet over medium-high heat.',
      'Cook protein until done (4-5 minutes for shrimp, 6-8 for chicken).',
      'Warm tortillas in a dry skillet or microwave.',
      'Prepare slaw by mixing cabbage with lime juice and a pinch of salt.',
      'Mix sour cream or mayo with lime juice for crema.',
      'Assemble tacos by layering tortillas with protein.',
      'Top with slaw, tomatoes, and avocado.',
      'Drizzle with crema and garnish with cilantro.',
      'Serve immediately with lime wedges.'
    ];
  }

  if (lowerName.includes('curry')) {
    return [
      'Cook rice according to package directions.',
      'Heat oil in a large pot or deep skillet over medium heat.',
      'Add onion and cook until softened, about 5 minutes.',
      'Add garlic and ginger, cook for 1 minute until fragrant.',
      'Stir in curry paste or powder and cook for 30 seconds.',
      'Add protein and cook until browned on all sides.',
      'Pour in coconut milk and bring to a simmer.',
      'Add vegetables and simmer for 10-15 minutes until tender.',
      'Season with salt and adjust spices to taste.',
      'Serve over rice, garnished with fresh cilantro.'
    ];
  }

  // Default instructions
  return [
    'Prepare all ingredients by washing, chopping, and measuring.',
    'Heat oil in a large pan over medium-high heat.',
    'Cook protein until browned and cooked through.',
    'Add aromatics and cook until fragrant.',
    'Add vegetables and other ingredients.',
    'Cook until everything is tender and well combined.',
    'Season to taste with salt and pepper.',
    'Garnish with fresh herbs.',
    'Serve hot and enjoy!'
  ];
}

function generateTips(mealName: string): string[] {
  const lowerName = mealName.toLowerCase();

  if (lowerName.includes('pasta')) {
    return [
      'Save some pasta water to thin the sauce if needed',
      'Don\'t rinse pasta after cooking - the starch helps sauce adhere',
      'Leftovers keep well in the fridge for up to 3 days'
    ];
  }

  if (lowerName.includes('salmon') || lowerName.includes('fish')) {
    return [
      'Check fish doneness by gently pressing - it should flake easily',
      'Don\'t overcook! Fish continues cooking after removing from heat',
      'Serve with a squeeze of fresh lemon for brightness'
    ];
  }

  if (lowerName.includes('stir fry') || lowerName.includes('beef')) {
    return [
      'Slice meat against the grain for maximum tenderness',
      'Have all ingredients prepped before starting - this cooks fast!',
      'Use day-old rice for the best texture and to prevent mushiness'
    ];
  }

  if (lowerName.includes('bowl')) {
    return [
      'Meal prep by preparing components separately and storing in containers',
      'Customize with your favorite toppings and sauces',
      'Make it vegan by omitting dairy and using plant-based protein'
    ];
  }

  if (lowerName.includes('meatball')) {
    return [
      'Don\'t overmix the meat mixture or meatballs will be tough',
      'Wet your hands when rolling meatballs to prevent sticking',
      'These freeze beautifully - make a double batch!'
    ];
  }

  if (lowerName.includes('taco')) {
    return [
      'Warm tortillas for better flavor and flexibility',
      'Prep toppings in advance for quick assembly',
      'Use any protein you like - fish, chicken, or beans work great'
    ];
  }

  if (lowerName.includes('curry')) {
    return [
      'Adjust curry paste amount based on your spice preference',
      'Add vegetables that take longer to cook first',
      'Tastes even better the next day as flavors meld together'
    ];
  }

  return [
    'Taste and adjust seasonings before serving',
    'Leftovers can be stored in the fridge for 3-4 days',
    'Feel free to substitute ingredients based on what you have'
  ];
}
