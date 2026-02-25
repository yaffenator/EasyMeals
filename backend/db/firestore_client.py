import firebase_admin
from firebase_admin import credentials, firestore
import os

def _init_db():
    if firebase_admin._apps:
        return firestore.client()
    
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not cred_path:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cred_path = os.path.join(BASE_DIR, "secrets", "serviceAccountKey.json")
    
    if not os.path.exists(cred_path):
        return None  # Let tests mock this, don't crash
    
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = _init_db()