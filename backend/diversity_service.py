from datetime import datetime, timedelta, timezone
from db.firestore_client import db
import math

ROLLING_WINDOW_DAYS = 14

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

