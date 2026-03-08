import { generateRecipeDetails } from "../recipeDetails";

describe("generateRecipeDetails instructions normalization", () => {
  it("keeps instruction arrays", () => {
    const details = generateRecipeDetails({
      name: "Test Meal",
      day: "Monday",
      instructions: ["Step 1", "Step 2"],
    });
    expect(details.instructions).toEqual(["Step 1", "Step 2"]);
  });

  it("splits newline instruction strings", () => {
    const details = generateRecipeDetails({
      name: "Test Meal",
      day: "Monday",
      instructions: "Step 1\nStep 2\nStep 3",
    });
    expect(details.instructions).toEqual(["Step 1", "Step 2", "Step 3"]);
  });

  it("splits sentence instruction strings", () => {
    const details = generateRecipeDetails({
      name: "Test Meal",
      day: "Monday",
      instructions: "Mix ingredients. Cook for 10 minutes. Serve warm.",
    });
    expect(details.instructions).toEqual([
      "Mix ingredients.",
      "Cook for 10 minutes.",
      "Serve warm.",
    ]);
  });

  it("normalizes inline numbered instructions", () => {
    const details = generateRecipeDetails({
      name: "Test Meal",
      day: "Monday",
      instructions: "1. Heat pan. 2. Add ingredients. 3. Serve.",
    });
    expect(details.instructions).toEqual([
      "Heat pan.",
      "Add ingredients.",
      "Serve.",
    ]);
  });

  it("normalizes newline numbered instructions", () => {
    const details = generateRecipeDetails({
      name: "Test Meal",
      day: "Monday",
      instructions: "1. Heat pan\n2. Add ingredients\n3. Serve",
    });
    expect(details.instructions).toEqual([
      "Heat pan",
      "Add ingredients",
      "Serve",
    ]);
  });
});
