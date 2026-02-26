import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';
import { CTA } from '../CTA';

// Mock the useRouter hook
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

describe('CTA Component', () => {
  it('should render the heading and button', () => {
    render(<CTA />);
    
    expect(screen.getByText('Ready to Start Saving?')).toBeInTheDocument();
    expect(screen.getByText('Your personalized, budget-friendly meal plan is just a click away.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Get Started for Completely Free!/i })).toBeInTheDocument();
  });

  it('should redirect to /login when the button is clicked', () => {
    const push = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({ push });

    render(<CTA />);
    
    const button = screen.getByRole('button', { name: /Get Started for Completely Free!/i });
    fireEvent.click(button);
    
    expect(push).toHaveBeenCalledWith('/login');
  });
});
