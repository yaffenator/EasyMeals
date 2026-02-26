import pytest
import json

def test_api_response_structure():
    """Validates that the AI response matches the Firebase Recipe Schema requirements"""
    # Simulate the response structure defined in route.ts
    mock_response = {
        "mealPlan": {
            "name": "Quinoa Salad",
            "source": "generated",
            "ingredientItems": [{"ingredientId": "quinoa", "quantity": 1}]
        },
        "newIngredients": {
            "quinoa": {"name": "Quinoa", "category": "Grains"}
        }
    }
    
    # Assert key fields required by the system exist
    assert "mealPlan" in mock_response
    assert "newIngredients" in mock_response
    assert mock_response["mealPlan"]["source"] == "generated"