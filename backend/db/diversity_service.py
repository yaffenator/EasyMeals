from datetime import datetime, timedelta, timezone
from db.firestore_client import db
import math
import random

ROLLING_WINDOW_DAYS = 14
LAMBDA = 0.5

def get_recent_meal_history(user_id: str) -> dict[str, int]:
    '''
    Fetching the user's meal history within the last 14 days
    returns a dict of {mealID: count} which is how many times
    each meal was eaten withing the last 14 days
    '''

    cutoff = datetime.now(timezone.utc) - timedelta(days=ROLLING_WINDOW_DAYS)

    #finds the user's meal history and filters by those within the 14 day window 
    history_ref = (
        db.collection("users")
        .document(user_id)
        .collection("mealHistory")
        .where("eatenAt", ">=", cutoff)
        .stream()
    )

    counts = {}

    for doc in history_ref:
        meal_id = doc.to_dict().get("mealId")
        if meal_id:
            counts[meal_id] = counts.get(meal_id, 0) + 1
    
    return counts

#diversity functions

def compute_diversity_weight(recent_count: int) -> float:
    """
    diversityWeight = e^(-λn)
    n = how many times user ate this meal in the rolling window
    λ = 0.5 (controls how fast the weight decays with repetition)

    If n=0 (never eaten recently), weight = e^0 = 1.0, no penalty.
    If n=1, weight = e^-0.5 ≈ 0.6, moderate penalty.
    If n=2, weight = e^-1.0 ≈ 0.37, heavy penalty.
    Never reaches 0, so meals are never hard-banned, just deprioritized.
    """
    return math.exp(-LAMBDA * recent_count)

def compute_final_scores(user_id: str, candidate_meals: list[dict]) -> list[dict]:
    """
    Takes a list of candidate meals and attaches a finalScore to each.
    finalScore = recommendationScore * diversityWeight

    candidate_meals should be a list of dicts with at least:
    { "mealId": str, "recommendationScore": float }
    """
    recent_history = get_recent_meal_history(user_id)
    
    scored_meals = []
    for meal in candidate_meals:
        meal_id = meal.get("mealID")
        recommendation_score = meal.get("recommendation_score", 0.0)
        recent_count = recent_history.get(meal_id, 0)

        diversity_weight = compute_diversity_weight(recent_count)
        final_score = recommendation_score * diversity_weight

        scored_meals.append({
            **meal,
            "diversityWeight": round(diversity_weight, 4),
            "finalScore": round(final_score, 4),
        })
    return scored_meals

def sample_meals(scored_meals: list[dict], n: int) -> list[dict]:

    """
    Selects n meals from scored_meals using weighted random sampling,
    where each meal's probability of being selected is proportional
    to its finalScore. This means high-scoring meals are likely to appear
    but not guaranteed, keeping plans varied while still favoring
    well-rated, non-repetitive meals.
    """

    if not scored_meals:
        return []
    
    weights = [meal.get("finalScore", 0.0) for meal in scored_meals]

    #edge case coverage of if all weights are 0 (fall back to uniform sampling.)
    if sum(weights) == 0:
        return random.sample(scored_meals, min(n, len(scored_meals)))
    
    selected = random.choices(scored_meals, weights=weights, k=n)

    return selected