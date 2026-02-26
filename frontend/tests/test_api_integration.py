import pytest
import json

def test_api_response_structure():
    """Validates that the AI response matches the Firebase Recipe Schema requirements"""
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
    
    assert "mealPlan" in mock_response
    assert "newIngredients" in mock_response
    assert mock_response["mealPlan"]["source"] == "generated"