import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from '../page';
import { loadMealPlan, clearMealPlan } from '../../utils/MealPlanGenerator';

// 1. Mock Firebase Auth Functions
jest.mock('firebase/auth', () => ({
  getAuth: jest.fn(),
  createUserWithEmailAndPassword: jest.fn().mockResolvedValue({ 
    user: { uid: '123', email: 'test@test.com' } 
  }),
  signInWithEmailAndPassword: jest.fn().mockResolvedValue({ 
    user: { uid: '123', email: 'test@test.com' } 
  }),
  updateProfile: jest.fn().mockResolvedValue(undefined),
  onAuthStateChanged: jest.fn(),
}));

// 2. Mock your Auth Context (Adjust the import path if needed based on your folder structure)
jest.mock('../../context/auth', () => ({
  useAuth: jest.fn().mockReturnValue({ 
    currentUser: { displayName: 'Test User', email: 'test@test.com' } 
  }),
}));

// Mock the utils
jest.mock('../../utils/MealPlanGenerator', () => ({
  ...jest.requireActual('../../utils/MealPlanGenerator'),
  loadMealPlan: jest.fn(),
  clearMealPlan: jest.fn(),
  saveMealPlan: jest.fn(),
  generateMealPlan: jest.fn().mockReturnValue({
    preferences: { monthlyBudget: 500 },
    weeks: [
      {
        weekNumber: 1,
        meals: [
          { id: '1', day: 'Monday', name: 'Test Meal', description: 'A test meal', image: 'https://example.com/image.jpg', prepTime: '30 min', cost: '$10', servings: 4, calories: 500, category: 'Dinner' }
        ]
      }
    ]
  })
}));

describe('Dashboard Page', () => {
  beforeEach(() => {
    (loadMealPlan as jest.Mock).mockClear();
    (clearMealPlan as jest.Mock).mockClear();
  });

  it('should show the welcome message and "Create" button when no meal plan exists', () => {
    (loadMealPlan as jest.Mock).mockReturnValue(null);
    render(<Dashboard />);

    expect(screen.getByText('Welcome to Your Meal Planner')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create Your Meal Plan/i })).toBeInTheDocument();
  });

  it('should show the meal plan details when a meal plan exists', () => {
    (loadMealPlan as jest.Mock).mockReturnValue({
      preferences: { monthlyBudget: 500 },
      weeks: [
        {
          weekNumber: 1,
          meals: [
            { id: '1', day: 'Monday', name: 'Test Meal', description: 'A test meal', image: 'https://example.com/image.jpg', prepTime: '30 min', cost: '$10', servings: 4, calories: 500, category: 'Dinner' }
          ]
        }
      ]
    });
    render(<Dashboard />);

    expect(screen.getByText('Your Meal Plan')).toBeInTheDocument();
    expect(screen.getByText('Weekly Cost')).toBeInTheDocument();
    expect(screen.getByText('Avg. Cost Per Meal')).toBeInTheDocument();
  });

  it('should open the wizard when "Create Your Meal Plan" is clicked', () => {
    (loadMealPlan as jest.Mock).mockReturnValue(null);
    render(<Dashboard />);

    const createButton = screen.getByRole('button', { name: /Create Your Meal Plan/i });
    fireEvent.click(createButton);

    // The wizard has a title "Create Your Meal Plan"
    expect(screen.getByRole('heading', { name: 'Create Your Meal Plan' })).toBeInTheDocument();
  });
});
