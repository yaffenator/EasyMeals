from db.firestore_client import db
from google.cloud import firestore as fs


#=========================================================
#            Purspose of this file is to
#            implement the rating system
#            for meals both globally & locally
#=========================================================

#minimum amount of ratings a meal has to have before their score is reliable
BAYESIAN_C = 10


def get_global_average() -> float:
    '''
    Reading the global average from a single met document instead of scanning through every meal
    Robust against a large meal database
    '''
    doc = db.collection("meta").document("globalStats").get()
    if doc.exists:
        return doc.to_dict().get("globalAvg", 3.0)
    #fallback if for some reason the document doesn't exist yet
    return 3.0

def update_global_stats(new_rating: int):
    '''
    Reads current totals, adds the new rating, recomputes globalAvg,
    then writes everything in a single update call.
    '''
    stats_ref = db.collection("meta").document("globalStats")
    
    current = stats_ref.get().to_dict() or {}
    new_sum = current.get("totalRatingSum", 0) + new_rating
    new_count = current.get("totalRatingCount", 0) + 1
    new_avg = new_sum / new_count

    stats_ref.update({
        "totalRatingSum": new_sum,
        "totalRatingCount": new_count,
        "globalAvg": new_avg,
        "updatedAt": fs.SERVER_TIMESTAMP,
    })

def compute_bayesian_score(R: float, v: int, m: float, C: int) -> float:
    '''
    Score = (v*R)+(m*C) / v+C 
    R = average rating for the meal
    𝑣 = number of ratings for the meal
    C = minimum ratings threshold (e.g., 10)
    𝑚 = global average rating across all meals
    '''

    '''
    When v is small relative to C, the score is pulled toward m (global avg).
    As v grows larger than C, the meal's own average R dominates the score.
    This prevents a meal with 2 five-star ratings from outranking a meal
    with 500 four-star ratings.
    '''

    return ((v*R) + (m*C)) / (v+C)

def rate_meal(meal_id: str, user_id: str, rating: int) -> dict:
    
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    
    meal_ref = db.collection("recipes").document(meal_id)
    meal_doc = meal_ref.get()

    if not meal_doc.exists:
        raise ValueError(f"Meal {meal_id} not found.")
    
    data = meal_doc.to_dict()

    #updating the meal's stats fields
    new_count = data.get("ratingCount", 0) + 1
    new_sum = data.get("ratingSum", 0.0) + rating 
    new_avg = new_sum / new_count

    m = get_global_average()
    new_score = compute_bayesian_score(new_avg, new_count, m, BAYESIAN_C)
    
    meal_ref.update({
        "ratingCount": new_count,
        "ratingSum": new_sum,
        "ratingAvg": new_avg,
        "recommendationScore": new_score,
        "updatedAt": fs.SERVER_TIMESTAMP,
    })

    meal_ref.collection("ratings").add({
        "uid": user_id,
        "rating": rating,
        "createdAt": fs.SERVER_TIMESTAMP
    })

    update_global_stats(rating)

    #return new meal stats
    return {
        "ratingCount": new_count,
        "ratingAvg": round(new_avg, 4),
        "recommendationScore": round(new_score, 4),
    }
