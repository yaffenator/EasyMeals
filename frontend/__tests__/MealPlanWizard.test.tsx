import { render, screen, fireEvent } from '@testing-library/react';
import { MealPlanWizard } from '../app/components/MealPlanWizard';

test('Next button is disabled if budget is empty', () => {
  render(<MealPlanWizard onComplete={() => {}} onCancel={() => {}} />);
  const nextButton = screen.getByRole('button', { name: /next/i });
  expect(nextButton).toBeDisabled(); // Validates 'canProceed' logic
});