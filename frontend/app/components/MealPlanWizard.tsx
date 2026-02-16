import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { RadioGroup, RadioGroupItem } from './ui/radioGroup';
import { Checkbox } from './ui/checkbox';
import { ChevronRight, ChevronLeft, Plus, X } from 'lucide-react';

interface MealPlanWizardProps {
  onComplete: (data: MealPlanData) => void;
  onCancel: () => void;
}

export interface MealPlanData {
  monthlyBudget: number;
  goal: 'lose' | 'gain' | 'maintain';
  allergies: string[];
  excludedCuisines: string[];
}

const commonAllergies = [
  'Milk',
  'Eggs',
  'Peanuts',
  'Tree Nuts',
  'Soy',
  'Wheat',
  'Fish',
  'Shellfish',
  'Sesame',
  'Corn',
  'Gluten',
  'Mustard',
  'Celery',
  'Lupin',
  'Sulfites'
];

export function MealPlanWizard({ onComplete, onCancel }: MealPlanWizardProps) {
  const [step, setStep] = useState(1);
  const [monthlyBudget, setMonthlyBudget] = useState('');
  const [goal, setGoal] = useState<'lose' | 'gain' | 'maintain'>('maintain');
  const [selectedAllergies, setSelectedAllergies] = useState<string[]>([]);
  const [otherAllergyChecked, setOtherAllergyChecked] = useState(false);
  const [customAllergies, setCustomAllergies] = useState<string[]>(['']);
  const [excludedCuisines, setExcludedCuisines] = useState('');

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1);
    } else {
      // Combine selected allergies with custom ones
      const allAllergies = [
        ...selectedAllergies,
        ...(otherAllergyChecked ? customAllergies.filter(a => a.trim() !== '') : [])
      ];

      const cuisineList = excludedCuisines
        .split(',')
        .map(c => c.trim())
        .filter(c => c !== '');

      onComplete({
        monthlyBudget: parseFloat(monthlyBudget),
        goal,
        allergies: allAllergies,
        excludedCuisines: cuisineList
      });
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const toggleAllergy = (allergy: string) => {
    setSelectedAllergies(prev =>
      prev.includes(allergy)
        ? prev.filter(a => a !== allergy)
        : [...prev, allergy]
    );
  };

  const addCustomAllergyField = () => {
    setCustomAllergies([...customAllergies, '']);
  };

  const updateCustomAllergy = (index: number, value: string) => {
    const updated = [...customAllergies];
    updated[index] = value;
    setCustomAllergies(updated);
  };

  const removeCustomAllergy = (index: number) => {
    if (customAllergies.length > 1) {
      setCustomAllergies(customAllergies.filter((_, i) => i !== index));
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return monthlyBudget !== '' && parseFloat(monthlyBudget) > 0;
      case 2:
        return !!goal;
      case 3:
      case 4:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle className="text-2xl text-primary">Create Your Meal Plan</CardTitle>
          <CardDescription>Step {step} of 4</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Step 1: Monthly Budget */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-xl mb-4">What's your monthly food budget?</h3>
                <Label htmlFor="budget">Monthly Budget ($)</Label>
                <Input
                  id="budget"
                  type="number"
                  placeholder="e.g., 400"
                  value={monthlyBudget}
                  onChange={(e) => setMonthlyBudget(e.target.value)}
                  className="mt-2"
                  min="0"
                  step="0.01"
                />
                <p className="text-sm text-muted-foreground mt-2">
                  Enter your total monthly budget for groceries and meals
                </p>
              </div>
            </div>
          )}

          {/* Step 2: Goals */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-xl mb-4">What's your health goal?</h3>
                <RadioGroup value={goal} onValueChange={(value: any) => setGoal(value)}>
                  <div className="flex items-center space-x-2 p-4 border rounded-lg hover:bg-accent cursor-pointer">
                    <RadioGroupItem value="lose" id="lose" />
                    <Label htmlFor="lose" className="cursor-pointer flex-1">
                      <div className="font-medium">Lose Weight</div>
                      <div className="text-sm text-muted-foreground">
                        Meals optimized for calorie deficit and weight loss
                      </div>
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-4 border rounded-lg hover:bg-accent cursor-pointer">
                    <RadioGroupItem value="maintain" id="maintain" />
                    <Label htmlFor="maintain" className="cursor-pointer flex-1">
                      <div className="font-medium">Maintain Weight</div>
                      <div className="text-sm text-muted-foreground">
                        Balanced meals to maintain your current weight
                      </div>
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-4 border rounded-lg hover:bg-accent cursor-pointer">
                    <RadioGroupItem value="gain" id="gain" />
                    <Label htmlFor="gain" className="cursor-pointer flex-1">
                      <div className="font-medium">Gain Weight</div>
                      <div className="text-sm text-muted-foreground">
                        Nutrient-dense meals for healthy weight gain
                      </div>
                    </Label>
                  </div>
                </RadioGroup>
              </div>
            </div>
          )}

          {/* Step 3: Allergies */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-xl mb-4">Do you have any food allergies?</h3>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  {commonAllergies.map((allergy) => (
                    <div key={allergy} className="flex items-center space-x-2">
                      <Checkbox
                        id={allergy}
                        checked={selectedAllergies.includes(allergy)}
                        onCheckedChange={() => toggleAllergy(allergy)}
                      />
                      <Label
                        htmlFor={allergy}
                        className="text-sm cursor-pointer"
                      >
                        {allergy}
                      </Label>
                    </div>
                  ))}
                </div>

                <div className="border-t pt-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Checkbox
                      id="other"
                      checked={otherAllergyChecked}
                      onCheckedChange={(checked) => setOtherAllergyChecked(checked as boolean)}
                    />
                    <Label htmlFor="other" className="cursor-pointer">
                      Other (specify below)
                    </Label>
                  </div>

                  {otherAllergyChecked && (
                    <div className="space-y-2 ml-6">
                      {customAllergies.map((allergy, index) => (
                        <div key={index} className="flex gap-2">
                          <Input
                            placeholder="Enter allergy"
                            value={allergy}
                            onChange={(e) => updateCustomAllergy(index, e.target.value)}
                            className="flex-1"
                          />
                          {customAllergies.length > 1 && (
                            <Button
                              type="button"
                              variant="outline"
                              size="icon"
                              onClick={() => removeCustomAllergy(index)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={addCustomAllergyField}
                        className="mt-2"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Add Another Allergy
                      </Button>
                    </div>
                  )}
                </div>

                <p className="text-sm text-muted-foreground mt-4">
                  Select all that apply. We'll exclude these ingredients from your meal plan.
                </p>
              </div>
            </div>
          )}

          {/* Step 4: Excluded Cuisines */}
          {step === 4 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-xl mb-4">Any cuisines or food types you want to avoid?</h3>
                <Label htmlFor="cuisines">Excluded Cuisines/Food Types (optional)</Label>
                <Input
                  id="cuisines"
                  placeholder="e.g., Italian, Seafood, Spicy foods"
                  value={excludedCuisines}
                  onChange={(e) => setExcludedCuisines(e.target.value)}
                  className="mt-2"
                />
                <p className="text-sm text-muted-foreground mt-2">
                  Separate multiple items with commas. Leave blank if you have no preferences.
                </p>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-8 pt-4 border-t">
            <Button
              variant="outline"
              onClick={step === 1 ? onCancel : handleBack}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              {step === 1 ? 'Cancel' : 'Back'}
            </Button>
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
              className="bg-primary hover:bg-primary/90"
            >
              {step === 4 ? 'Generate Meal Plan' : 'Next'}
              {step !== 4 && <ChevronRight className="w-4 h-4 ml-2" />}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
