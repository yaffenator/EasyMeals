import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase exactly ONCE in this file
if not firebase_admin._apps:
    firebase_env_creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    
    if firebase_env_creds:
        # We are on Render
        cred_dict = json.loads(firebase_env_creds)
        cred = credentials.Certificate(cred_dict)
    else:
        # We are running locally
        cred = credentials.Certificate("secrets/serviceAccountKey.json")
        
    firebase_admin.initialize_app(cred)

# Export the connected database for all other files to use!
db = firestore.client()