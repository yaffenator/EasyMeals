import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import Dashboard from '../app/dashboard/page';

test('renders welcome message on first load', () => {
  render(<Dashboard />);
  expect(screen.getByText(/Welcome to Your Meal Planner/i)).toBeInTheDocument();
});