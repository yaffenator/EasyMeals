// utils/firebaseClient.ts
import { initializeApp, getApps } from "firebase/app";
import { getFirestore } from "firebase/firestore";

/**
 * Uses env vars so you don't hardcode secrets in git.
 * Add these to .env.local (Next.js):
 * NEXT_PUBLIC_FIREBASE_API_KEY=...
 * NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
 * NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
 * NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
 * NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
 * NEXT_PUBLIC_FIREBASE_APP_ID=...
 */
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET!,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID!,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);

export const db = getFirestore(app);
