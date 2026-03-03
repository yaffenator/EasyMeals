import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

# 1. Setup
cred = credentials.Certificate("../secrets/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. Load the JSON
with open("../../frontend/ai-response.json", "r") as f:
    data = json.load(f)

def upload_recipe(recipe_data):
    # Prepare the ingredientItems with Document References
    processed_ingredient_items = []
    for item in recipe_data.get("ingredientItems", []):
        ing_id = item.get("ingredientId")
        
        # Create the reference: /ingredients/ingredient_id
        ing_ref = db.collection("ingredients").document(ing_id)
        
        # Build the map exactly like your database layout
        processed_item = {
            "ingredientId": ing_id,
            "ingredientRef": ing_ref, # This stores as a Reference type
            "originalText": item.get("originalText"),
            "quantity": item.get("quantity"),
            "unit": item.get("unit", ""),
            "notes": item.get("notes", "")
        }
        processed_ingredient_items.append(processed_item)

    # Construct the final document
    # Note: I'm converting 'carbs', 'fat', and 'protein' to strings like your layout
    firestore_doc = {
        "name": recipe_data.get("name"),
        "calories": recipe_data.get("calories"),
        "carbs": f"{recipe_data.get('carbs')}g",
        "fat": f"{recipe_data.get('fat')}g",
        "protein": f"{recipe_data.get('protein')}g",
        "cookTime": recipe_data.get("cookTime"),
        "prepTime": recipe_data.get("prepTime"),
        "servings": recipe_data.get("servings"),
        "costPerServing": recipe_data.get("costPerServing"),
        "totalCost": recipe_data.get("totalCost"),
        "mealType": recipe_data.get("mealType"),
        "difficulty": recipe_data.get("difficulty").capitalize(),
        "instructions": recipe_data.get("instructions"), # Already an array
        "ingredients": recipe_data.get("ingredients"),   # Already an array
        "ingredientItems": processed_ingredient_items,
        "tags": recipe_data.get("tags"),
        "tips": recipe_data.get("tips"),
        "source": recipe_data.get("source"),
        "createdAt": datetime.fromisoformat(recipe_data.get("createdAt").replace("Z", "+00:00")),
        "updatedAt": datetime.now() # Set current time as update
    }

    # Also include the nutritionInfo map found in your layout
    firestore_doc["nutritionInfo"] = {
        "calories": str(recipe_data.get("calories")),
        "carbs": f"{recipe_data.get('carbs')}g",
        "fat": f"{recipe_data.get('fat')}g",
        "protein": f"{recipe_data.get('protein')}g"
    }

    # Upload to the 'recipes' collection
    db.collection("recipes").add(firestore_doc)
    print(f"Successfully uploaded: {recipe_data.get('name')}")

# Run the upload for all recipes in the mealPlan list
for recipe in data.get("mealPlan", []):
    upload_recipe(recipe)