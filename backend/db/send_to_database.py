import firebase_admin
from firebase_admin import credentials, firestore
import json

# 1. Initialize Firebase
# Replace 'serviceAccountKey.json' with your actual file path
cred = credentials.Certificate("secrets/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. Load your JSON file
# Replace 'meal_data.json' with the name of your file
with open("meal_data.json", "r") as f:
    data = json.load(f)

# 3. Upload mealPlan to 'recipes' collection
print("Uploading recipes...")
recipes = data.get("mealPlan", [])
for recipe in recipes:
    # Use .add() to let Firestore auto-generate a unique ID for each recipe
    db.collection("recipes").add(recipe)

# 4. Upload newIngredients to 'ingredients' collection
print("Uploading ingredients...")
ingredients = data.get("newIngredients", {})
for ingredient_id, details in ingredients.items():
    # Use the key (e.g., 'chicken_breast') as the Document ID
    db.collection("ingredients").document(ingredient_id).set(details)

print("Finished! Your database is now populated.")