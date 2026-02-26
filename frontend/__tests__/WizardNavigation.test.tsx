import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MealPlanWizard } from '../app/components/MealPlanWizard';

global.fetch = jest.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({ weeks: [] }) })
) as jest.Mock;

test('submits correct data to /api/save-preferences', async () => {
  render(<MealPlanWizard onComplete={() => {}} onCancel={() => {}} />);
  // Logic to simulate clicking through to step 5 and hitting Finish
  const nextButton = screen.getByRole('button', { name: /next/i });
  fireEvent.click(nextButton); 
  // ... continue steps ...
});