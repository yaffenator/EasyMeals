import os
from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import credentials, firestore


def init_firestore():
    """
    Initialize Firebase Admin SDK.
    Uses GOOGLE_APPLICATION_CREDENTIALS if set, otherwise falls back to ./serviceAccountKey.json
    """
    if not firebase_admin._apps:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            # Fallback: put your key next to this file (NOT recommended for real repos)
            fallback = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if not os.path.exists(fallback):
                raise FileNotFoundError(
                    "No service account key found. Set GOOGLE_APPLICATION_CREDENTIALS "
                    "or place serviceAccountKey.json next to seed_firestore.py."
                )
            cred = credentials.Certificate(fallback)

        firebase_admin.initialize_app(cred)

    return firestore.client()


def seed(db: firestore.Client):
    now = datetime.now(timezone.utc)

    # ---- ingredients (global) ----
    ingredient_id = "dummy_ingredient_chicken_breast"
    db.collection("ingredients").document(ingredient_id).set({
        "name": "chicken breast",
        "aliases": ["chicken breasts", "boneless chicken breast", "skinless chicken breast"],
        "category": "meat",
        "defaultUnit": "g",
        "snapEligibleDefault": True,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })

    # ---- meals (global) ----
    meal_id = "dummy_meal_grilled_chicken_rice"
    db.collection("meals").document(meal_id).set({
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "title": "Grilled Chicken and Rice",
        "description": "Simple high-protein meal (dummy).",
        "cuisine": "American",
        "tags": ["high_protein", "budget_friendly"],
        "servings": 2,
        "prepTimeMins": 10,
        "cookTimeMins": 20,
        "instructions": ["Season chicken", "Grill chicken", "Cook rice", "Serve"],
        "nutrition": {"calories": 550, "proteinG": 45, "carbsG": 55, "fatG": 15},
        "ingredients": [
            {"ingredientId": ingredient_id, "name": "chicken breast", "quantity": 300, "unit": "g", "isStaple": False},
            {"ingredientId": "dummy_ingredient_rice", "name": "rice", "quantity": 200, "unit": "g", "isStaple": True},
        ],
        "ratingCount": 0,
        "ratingAvg": 0.0,
        "recommendationScore": 0.0,
    })

    # ---- stores (global) ----
    store_id = "dummy_store_1"
    db.collection("stores").document(store_id).set({
        "name": "Dummy Market",
        "chain": "DummyChain",
        "supported": True,
        "geo": {"zipCodes": ["97201"]},
        "lastScrapeAt": None,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })

    # ---- storeItems (global) ----
    store_item_id = f"{store_id}_{ingredient_id}"
    db.collection("storeItems").document(store_item_id).set({
        "storeId": store_id,
        "ingredientId": ingredient_id,
        "productName": "Boneless Chicken Breast Family Pack (Dummy)",
        "productUrl": None,
        "unitSize": {"quantity": 32, "unit": "oz"},
        "snapEligible": True,
        "inStock": True,
        "currentPrice": 9.99,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "createdAt": firestore.SERVER_TIMESTAMP,
    })

    # ---- users (global collection, per uid doc) ----
    # For seeding: use a predictable dummy uid
    uid = "dummy_uid_123"
    db.collection("users").document(uid).set({
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "displayName": "Dummy User",
        "email": "dummy@example.com",

        "zipCode": "97201",
        "monthlyBudget": 250,
        "snapEnabled": True,
        "snapMonthlyBenefit": 200,
        "snapRemainingBenefit": 200,

        "goalType": "lose",
        "goalIntensity": "medium",
        "calorieTarget": 2000,
        "macroTargets": {"proteinG": 140, "carbsG": 200, "fatG": 60},
        "activityLevel": "moderate",

        "allergies": [],
        "dietaryTags": ["high_protein"],
        "dislikedIngredients": ["olives"],
        "cuisinePreferences": ["mexican", "american"],
        "cookingTimePreferenceMins": 30,
    })

    # ---- users/{uid}/mealHistory (subcollection) ----
    db.collection("users").document(uid).collection("mealHistory").add({
        "mealId": meal_id,
        "planId": None,
        "eatenAt": now,
        "servings": 1,
    })

    # ---- users/{uid}/plans/{planId} ----
    plan_id = "dummy_plan_1"
    plan_ref = db.collection("users").document(uid).collection("plans").document(plan_id)
    plan_ref.set({
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "status": "ready",
        "period": {
            "type": "week",
            "start": now,
            "end": now + timedelta(days=7),
        },
        "inputs": {
            "monthlyBudget": 250,
            "goalType": "lose",
            "dietaryTags": ["high_protein"],
            "allergies": [],
            "zipCode": "97201",
        },
        "totals": {
            "estimatedTotal": 42.50,
            "snapEligibleTotal": 42.50,
            "cashRequiredTotal": 0.0,
            "caloriesPerDayAvg": 2000,
        },
        "generation": {
            "model": "dummy",
            "promptVersion": "v0",
            "generatedAt": now,
            "warnings": [],
        }
    })

    # ---- users/{uid}/plans/{planId}/days/{dayId} ----
    plan_ref.collection("days").document("day_1").set({
        "date": now,
        "meals": [{"mealId": meal_id, "servings": 1, "finalScore": 0.0}],
    })

    # ---- users/{uid}/plans/{planId}/groceryItems/{itemId} ----
    plan_ref.collection("groceryItems").document(ingredient_id).set({
        "ingredientId": ingredient_id,
        "name": "chicken breast",
        "totalQuantity": 300,
        "unit": "g",
        "chosenStoreId": store_id,
        "chosenStoreItemId": store_item_id,
        "estimatedPrice": 9.99,
        "snapEligible": True,
        "inPantry": False,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })

    # ---- meals/{mealId}/ratings/{ratingId} (subcollection) ----
    db.collection("meals").document(meal_id).collection("ratings").add({
        "uid": uid,
        "rating": 5,
        "createdAt": now,
    })

    print("Seed complete.")
    print("Created docs in: ingredients, meals, stores, storeItems, users (+ subcollections).")


if __name__ == "__main__":
    db = init_firestore()
    seed(db)
