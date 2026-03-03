import { initializeApp } from "firebase/app";
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
  deleteDoc,
} from "firebase/firestore";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_apiKey,
  authDomain: process.env.NEXT_PUBLIC_authDomain,
  projectId: process.env.NEXT_PUBLIC_projectId,
  storageBucket: process.env.NEXT_PUBLIC_storageBucket,
  messagingSenderId: process.env.NEXT_PUBLIC_messagingSenderId,
  appId: process.env.NEXT_PUBLIC_appId,
  measurementId: process.env.NEXT_PUBLIC_measurementId,
};

const app = initializeApp(firebaseConfig);
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
    const mealPlanCollectionRef = collection(db, "users", uid, "mealPlan");

    // Delete existing plan docs before saving new plan
    const existingDocs = await getDocs(mealPlanCollectionRef);
    await Promise.all(existingDocs.docs.map((mealDoc) => deleteDoc(mealDoc.ref)));

    const mealsToSave = Array.isArray(mealPlan)
      ? mealPlan
      : (mealPlan.weeks || []).flatMap((week) =>
          (week.meals || []).map((meal) => ({
            ...meal,
            weekNumber: week.weekNumber,
          })),
        );

    for (const recipeData of mealsToSave) {
      const processedIngredientItems = (recipeData.ingredientItems || []).map((item) => ({
        ...item,
        ingredientRef: item.ingredientId ? doc(db, "ingredients", item.ingredientId) : null,
      }));

      const difficulty = recipeData.difficulty || "Medium";

      const firestoreDoc = {
        ...recipeData,
        day: recipeData.day || "Monday",
        weekNumber: Number(recipeData.weekNumber) || 1,
        carbs: typeof recipeData.carbs === "number" ? `${recipeData.carbs}g` : recipeData.carbs,
        fat: typeof recipeData.fat === "number" ? `${recipeData.fat}g` : recipeData.fat,
        protein: typeof recipeData.protein === "number" ? `${recipeData.protein}g` : recipeData.protein,
        difficulty: difficulty.charAt(0).toUpperCase() + difficulty.slice(1),
        ingredientItems: processedIngredientItems,
        ownerId: uid,
        status: "completed",
        updatedAt: serverTimestamp(),
      };

      await addDoc(mealPlanCollectionRef, firestoreDoc);
    }

    console.log("Meal plan replaced and synced to user mealPlan subcollection.");
  } catch (error) {
    console.error("Error syncing Gemini plan:", error);
    throw error;
  }
};

export const loadMealPlanFromFirestore = async (uid) => {
  if (!uid) return null;

  try {
    const mealPlanCollectionRef = collection(db, "users", uid, "mealPlan");
    const [querySnapshot, userSnap] = await Promise.all([
      getDocs(mealPlanCollectionRef),
      getDoc(doc(db, "users", uid)),
    ]);

    if (querySnapshot.empty) {
      return null;
    }

    const meals = querySnapshot.docs.map((mealDoc) => ({ id: mealDoc.id, ...mealDoc.data() }));

    const weeksMap = new Map();

    for (const meal of meals) {
      const weekNumber = Number(meal.weekNumber) || 1;
      const normalizedMeal = {
        ...meal,
        id: meal.id,
        day: meal.day || DAYS[0],
        status: meal.status || "completed",
        prepTime: meal.prepTime || "0 min",
        totalCost: meal.totalCost || "$0.00",
        calories: Number(meal.calories) || 0,
        description: meal.description || "",
        image: meal.image || "/api/placeholder/400/300",
      };

      if (!weeksMap.has(weekNumber)) {
        weeksMap.set(weekNumber, []);
      }

      weeksMap.get(weekNumber).push(normalizedMeal);
    }

    const weeks = Array.from(weeksMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([weekNumber, weekMeals]) => ({
        weekNumber,
        meals: weekMeals.sort((a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day)),
      }));

    const userData = userSnap.exists() ? userSnap.data() : {};
    const profile = userData.mealPlanProfile || {};

    return {
      preferences: {
        monthlyBudget: profile.monthlyBudget || 0,
        goal: profile.goal || "maintain",
        currentWeight: profile.weight || 0,
        allergies: profile.allergies || [],
        excludedCuisines: profile.excludedCuisines || [],
      },
      weeks,
      createdAt: new Date().toISOString(),
    };
  } catch (error) {
    console.error("Error loading meal plan from Firestore:", error);
    return null;
  }
};
