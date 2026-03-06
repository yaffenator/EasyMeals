import { getApps, initializeApp } from "firebase/app";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
  GoogleAuthProvider,
  GithubAuthProvider,
  signInWithPopup,
} from "firebase/auth";
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  updateDoc,
  serverTimestamp,
  collection,
  addDoc,
  getDocs,
  query,
  orderBy,
  limit,
  deleteDoc,
} from "firebase/firestore";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || process.env.NEXT_PUBLIC_apiKey,
  authDomain:
    process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || process.env.NEXT_PUBLIC_authDomain,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || process.env.NEXT_PUBLIC_projectId,
  storageBucket:
    process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || process.env.NEXT_PUBLIC_storageBucket,
  messagingSenderId:
    process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID ||
    process.env.NEXT_PUBLIC_messagingSenderId,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || process.env.NEXT_PUBLIC_appId,
  measurementId:
    process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || process.env.NEXT_PUBLIC_measurementId,
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

const googleProvider = new GoogleAuthProvider();
const githubProvider = new GithubAuthProvider();
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export const registerUser = async (email, password, name) => {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(userCredential.user, { displayName: name });
    await saveUserToDatabase(userCredential.user, { displayName: name });
    return userCredential.user;
  } catch (error) {
    throw error;
  }
};

export const loginUser = async (email, password) => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
};

export const loginWithGoogle = async () => {
  try {
    const userCredential = await signInWithPopup(auth, googleProvider);
    await saveUserToDatabase(userCredential.user);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
};

export const loginWithGithub = async () => {
  try {
    const userCredential = await signInWithPopup(auth, githubProvider);
    await saveUserToDatabase(userCredential.user);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
};

export const logoutUser = async () => {
  try {
    await auth.signOut();
  } catch (error) {
    throw error;
  }
};

export const saveUserToDatabase = async (user, additionalData = {}) => {
  if (!user) return;

  const userRef = doc(db, "users", user.uid);
  const userSnap = await getDoc(userRef);

  if (!userSnap.exists()) {
    try {
      await setDoc(userRef, {
        uid: user.uid,
        email: user.email,
        displayName:
          user.displayName || additionalData.displayName || user.email.split("@")[0] || "Chef",
        createdAt: serverTimestamp(),
        ...additionalData,
      });
    } catch (error) {
      console.error("Error creating user document", error);
    }
  }
};

export const updateUserPreferences = async (uid, preferencesData) => {
  if (!uid) return;

  try {
    const userRef = doc(db, "users", uid);
    await updateDoc(userRef, {
      mealPlanProfile: {
        questionnaireCompleted: preferencesData.questionnaireCompleted || true,
        allergies: preferencesData.allergies || [],
        excludedCuisines: preferencesData.excludedCuisines || [],
        goal: preferencesData.goal || "maintain",
        monthlyBudget: preferencesData.monthlyBudget || 0,
        weight: preferencesData.currentWeight || 0,
        version: 1,
        completedAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      },
    });
    console.log("Preferences saved successfully!");
  } catch (error) {
    console.error("Error saving preferences:", error);
    throw error;
  }
};

export const uploadMealPlanToUser = async (uid, mealPlan) => {
  if (!uid || !mealPlan) return;

  try {
    const userRef = doc(db, "users", uid);
    const plansRef = collection(db, "users", uid, "plans");
    const nowIso = new Date().toISOString();
    
    // Primary aligned write path: users/{uid}/plans/{planId}
    await addDoc(plansRef, {
      ...mealPlan,
      status: mealPlan.status || "ready",
      createdAt: nowIso,
      updatedAt: nowIso,
    });

    // Backward-compatible mirror to legacy field.
    await setDoc(
      userRef,
      {
        uid,
        currentMealPlan: {
          ...mealPlan,
          updatedAt: nowIso,
        },
        updatedAt: nowIso,
      },
      { merge: true },
    );

    console.log("Meal plan synced successfully.");
  } catch (error) {
    console.error("Error syncing meal plan:", error);
    throw error;
  }
};

export const loadMealPlanFromFirestore = async (uid) => {
  if (!uid) return null;

  try {
    const plansRef = collection(db, "users", uid, "plans");
    const latestPlanQuery = query(plansRef, orderBy("createdAt", "desc"), limit(1));
    const planSnap = await getDocs(latestPlanQuery);

    if (!planSnap.empty) {
      return planSnap.docs[0].data();
    }

    // Backward-compatible fallback.
    const userSnap = await getDoc(doc(db, "users", uid));
    if (userSnap.exists()) {
      const data = userSnap.data();
      return data.currentMealPlan || null;
    }
    return null;
  } catch (error) {
    console.error("Error loading meal plan:", error);
    return null;
  }
};
