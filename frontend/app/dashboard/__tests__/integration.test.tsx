import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from '../page';
import * as MealPlanGenerator from '../../utils/MealPlanGenerator';

// We will not mock the generator, but we will spy on it to make sure it is called.
jest.mock('../../utils/MealPlanGenerator', () => ({
    ...jest.requireActual('../../utils/MealPlanGenerator'),
    generateMealPlan: jest.fn(),
}));

describe('Meal Plan Generation Flow', () => {
    beforeEach(() => {
        // Before each test, clear localStorage
        window.localStorage.clear();
        (MealPlanGenerator.generateMealPlan as jest.Mock).mockClear();
    });

    it('should allow a user to create a meal plan and see it on the dashboard', async () => {
        (MealPlanGenerator.generateMealPlan as jest.Mock).mockImplementation((data) => ({
            preferences: data,
            weeks: [
                {
                    weekNumber: 1,
                    meals: [
                        { id: '1', day: 'Monday', name: 'Generated Meal', description: 'A meal generated from test', image: 'https://example.com/image.jpg', prepTime: '20 min', cost: '$12', servings: 4, calories: 550, category: 'Dinner' }
                    ]
                }
            ],
            createdAt: new Date().toISOString(),
        }));

        render(<Dashboard />);

        // 1. Start by clicking "Create Your Meal Plan"
        const createButton = screen.getByRole('button', { name: /Create Your Meal Plan/i });
        fireEvent.click(createButton);

        // Wizard should be visible
        expect(screen.getByRole('heading', { name: 'Create Your Meal Plan' })).toBeInTheDocument();

        // 2. Fill out the wizard - Step 1: Budget
        const budgetInput = screen.getByLabelText('Monthly Budget ($)');
        fireEvent.change(budgetInput, { target: { value: '500' } });
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));

        // 3. Step 2: Goal
        // The radio group for goals should be visible
        await screen.findByText("What's your health goal?");
        const maintainGoal = screen.getByLabelText(/Maintain Weight/i);
        fireEvent.click(maintainGoal);
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));

        // 4. Step 3: Allergies
        await screen.findByText('Do you have any food allergies?');
        const peanutsCheckbox = screen.getByLabelText('Peanuts');
        fireEvent.click(peanutsCheckbox);
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));

        // 5. Step 4: Excluded Cuisines
        await screen.findByText('Any cuisines or food types you want to avoid?');
        const cuisinesInput = screen.getByLabelText('Excluded Cuisines/Food Types (optional)');
        fireEvent.change(cuisinesInput, { target: { value: 'Italian' } });

        // 6. Generate Meal Plan
        const generateButton = screen.getByRole('button', { name: /Generate Meal Plan/i });
        fireEvent.click(generateButton);

        // 7. Verify the meal plan is on the dashboard
        await waitFor(() => {
            expect(screen.getByText('Your Meal Plan')).toBeInTheDocument();
        });

        expect(screen.getByText('Weekly Cost')).toBeInTheDocument();
        expect(screen.getByText('Avg. Cost Per Meal')).toBeInTheDocument();

        // Check if generateMealPlan was called with the correct data
        expect(MealPlanGenerator.generateMealPlan).toHaveBeenCalledWith({
            monthlyBudget: 500,
            goal: 'maintain',
            allergies: ['Peanuts'],
            excludedCuisines: ['Italian'],
        });
    });

    it('should correctly display a meal plan with a different structure', async () => {
        (MealPlanGenerator.generateMealPlan as jest.Mock).mockImplementation((data) => ({
            preferences: data,
            weeks: [
                {
                    weekNumber: 1,
                    meals: [
                        { id: '1', day: 'Monday', name: 'System Test Meal 1', description: 'A different meal', image: 'https://example.com/image.jpg', prepTime: '45 min', cost: '$15', servings: 2, calories: 700, category: 'Dinner' }
                    ]
                },
                {
                    weekNumber: 2,
                    meals: [
                        { id: '2', day: 'Tuesday', name: 'System Test Meal 2', description: 'Another different meal', image: 'https://example.com/image2.jpg', prepTime: '15 min', cost: '$8', servings: 4, calories: 400, category: 'Lunch' }
                    ]
                }
            ],
            createdAt: new Date().toISOString(),
        }));

        render(<Dashboard />);

        // Create a meal plan to trigger the display
        fireEvent.click(screen.getByRole('button', { name: /Create Your Meal Plan/i }));
        fireEvent.change(screen.getByLabelText('Monthly Budget ($)'), { target: { value: '800' } });
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        await screen.findByText("What's your health goal?");
        fireEvent.click(screen.getByLabelText(/Gain Weight/i));
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        await screen.findByText('Do you have any food allergies?');
        fireEvent.click(screen.getByRole('button', { name: /Next/i }));
        await screen.findByText('Any cuisines or food types you want to avoid?');
        fireEvent.click(screen.getByRole('button', { name: /Generate Meal Plan/i }));


        await waitFor(() => {
            expect(screen.getByText('Your Meal Plan')).toBeInTheDocument();
        });

        // Check for week 1 and 2 buttons
        expect(screen.getByRole('button', { name: 'Week 1' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Week 2' })).toBeInTheDocument();

        // Check that the first meal is displayed
        expect(screen.getByText('System Test Meal 1')).toBeInTheDocument();

        // Switch to week 2
        fireEvent.click(screen.getByRole('button', { name: 'Week 2' }));

        // Check that the second meal is displayed
        await waitFor(() => {
            expect(screen.getByText('System Test Meal 2')).toBeInTheDocument();
        });
    });
});
