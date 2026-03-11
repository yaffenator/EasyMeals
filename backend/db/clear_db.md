RUN THIS FROM THE BACKEND FOLDER TO CLEAR FIRESTORE DOCUMENTS

python db/clear_db.py

Optional flags:

- Specific collections:
  `python db/clear_db.py --collections users recipes ingredients meta`
- Project override:
  `python db/clear_db.py --project YOUR_PROJECT_ID`
- Delete one specific user tree first:
  `python db/clear_db.py --user-id test_user_1`

By default, the script now creates `_keepalive` in each cleared top-level
collection so collections remain visible in Firestore console.

Credentials lookup order:
1) `FIREBASE_SERVICE_ACCOUNT` (JSON string)
2) `backend/secrets/serviceAccountKey.json`
3) `backend/serviceAccountKey.json`
