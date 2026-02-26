import pytest

def calculate_budget_limit(monthly_budget):
    """Simulates the 60% budget rule defined in route.ts"""
    return monthly_budget * 0.60

def test_meal_plan_budget_rule():
    # Test Case: Ensure the logic correctly calculates the 60% threshold
    monthly_budget = 400
    limit = calculate_budget_limit(monthly_budget)
    
    assert limit == 240 # 60% of 400
    assert limit < monthly_budget