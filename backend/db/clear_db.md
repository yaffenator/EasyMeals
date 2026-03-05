RUN THIS FROM THE BACKEND FOLDER TO CLEAR FIRESTORE DOCUMENTS

python db/clear_db.py

Optional flags:

- Specific collections:
  `python db/clear_db.py --collections users recipes ingredients meta`
- Project override:
  `python db/clear_db.py --project YOUR_PROJECT_ID`

Credentials lookup order:
1) `GOOGLE_APPLICATION_CREDENTIALS`
2) `backend/secrets/serviceAccountKey.json`
3) `backend/serviceAccountKey.json`
