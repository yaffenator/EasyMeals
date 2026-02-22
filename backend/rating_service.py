from db.firestore_client import db
from google.cloud import firestore as fs


#=========================================================
#            Purspose of this file is to
#            implement the rating system
#            for meals both globally & locally
#=========================================================

#minimum amount of ratings a meal has to have before their score is reliable
BAYESIAN_MIN = 10


def get_global_average_rating() -> float:
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
    incrementing the 'totalRatingSum' and 'totalRatingCount' fields for globalStats
    then recomputes globalAvg. 
    '''
    stats_ref = db.collection("meta").document("globalStats")
    stats_ref.update({
        "totalRatingSum": fs.Increment(new_rating),
        "totalRatingCount": fs.Increment(1),
        "updatedAt": fs.SERVER_TIMESTAMP,
    })

    #recompute and store the new average
    updated = stats_ref.get().to_dict()
    new_avg = updated["totalRatingSum"] / updated["totalRatingCount"]
    stats_ref.update({"globalAvg": new_avg})



