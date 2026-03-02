import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MealPlanWizard } from '../MealPlanWizard';

describe('MealPlanWizard', () => {
  const onComplete = jest.fn();
  const onCancel = jest.fn();

  beforeEach(() => {
    onComplete.mockClear();
    onCancel.mockClear();
  });

  it('should disable the "Next" button in Step 1 if budget is not set', () => {
    render(<MealPlanWizard onComplete={onComplete} onCancel={onCancel} />);

    // Step 1 is visible by default
    expect(screen.getByText("What's your monthly food budget?")).toBeVisible();

    // Next button should be disabled
    const nextButton = screen.getByRole('button', { name: /Next/i });
    expect(nextButton).toBeDisabled();
  });

  it('should disable the "Next" button in Step 1 if budget is zero', () => {
    render(<MealPlanWizard onComplete={onComplete} onCancel={onCancel} />);
    const budgetInput = screen.getByLabelText('Monthly Budget ($)');

    fireEvent.change(budgetInput, { target: { value: '0' } });

    const nextButton = screen.getByRole('button', { name: /Next/i });
    expect(nextButton).toBeDisabled();
  });

  it('should enable the "Next" button in Step 1 when a valid budget is entered', () => {
    render(<MealPlanWizard onComplete={onComplete} onCancel={onCancel} />);
    const budgetInput = screen.getByLabelText('Monthly Budget ($)');

    fireEvent.change(budgetInput, { target: { value: '400' } });

    const nextButton = screen.getByRole('button', { name: /Next/i });
    expect(nextButton).toBeEnabled();
  });
});
