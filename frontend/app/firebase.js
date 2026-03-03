import { initializeApp } from "firebase/app";
import { 
  getAuth, 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  updateProfile,
  GoogleAuthProvider,
  GithubAuthProvider,
  signInWithPopup
} from "firebase/auth";
import { getFirestore, doc, setDoc, getDoc, updateDoc, serverTimestamp,collection, addDoc, arrayUnion } from "firebase/firestore";
import { UserPlus } from "lucide-react";

// firebase configuration object that uses environment variables to store sensitive information
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_apiKey,
  authDomain: process.env.NEXT_PUBLIC_authDomain,
  projectId: process.env.NEXT_PUBLIC_projectId,
  storageBucket: process.env.NEXT_PUBLIC_storageBucket,
  messagingSenderId: process.env.NEXT_PUBLIC_messagingSenderId,
  appId: process.env.NEXT_PUBLIC_appId,
  measurementId: process.env.NEXT_PUBLIC_measurementId,
};

// initialize firebase app, auth, and firestore (database connection)
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

// create google and github auth providers
const googleProvider = new GoogleAuthProvider();
const githubProvider = new GithubAuthProvider();

// email password registration function that takes in an email, password, and name and returns the user if the registration is successful, otherwise throws an error
export const registerUser = async (email, password, name) => {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(userCredential.user, { displayName: name });
    await saveUserToDatabase(userCredential.user, { displayName: name });
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

// email password login function that takes in an email and password and returns the user if the login is successful, otherwise throws an error
export const loginUser = async (email, password) => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

// google sign in function that uses the GoogleAuthProvider to sign in with a popup and returns the user if the login is successful, otherwise throws an error
export const loginWithGoogle = async () => {
  try {
    const userCredential = await signInWithPopup(auth, googleProvider);
    await saveUserToDatabase(userCredential.user);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

// github sign in function that uses the GithubAuthProvider to sign in with a popup and returns the user if the login is successful, otherwise throws an error
export const loginWithGithub = async () => {
  try {
    const userCredential = await signInWithPopup(auth, githubProvider);
    await saveUserToDatabase(userCredential.user);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

// logout function that signs the user out and returns a promise that resolves if the logout is successful, otherwise throws an error
export const logoutUser = async () => {
  try {
    await auth.signOut();
  } catch (error) {
    throw error;
  }
}

// Function to save user data to Firestore. It checks if the user already exists in the 'users' collection, and if not, it creates a new document with the user's information. It also accepts additional data that can be merged into the user document.
export const saveUserToDatabase = async (user, additionalData = {}) => {
  if (!user) return;

  // Create a reference to the 'users' collection, using the user's UID as the document ID
  const userRef = doc(db, "users", user.uid);
  const userSnap = await getDoc(userRef);

  // If the user doesn't exist in the database yet, create them!
  if (!userSnap.exists()) {
    try {
      await setDoc(userRef, {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName || additionalData.displayName || user.email.split("@")[0] || "Chef", // Fallback name
        createdAt: serverTimestamp(), // Firebase's built-in timestamp
        ...additionalData // Any extra data you want to pass in
      });
    } catch (error) {
      console.error("Error creating user document", error);
    }
  }
};

// Function to update user preferences in Firestore. It takes the user's UID and the new preferences data, and updates the corresponding document in the 'users' collection.
export const updateUserPreferences = async (uid, preferencesData) => {
  if (!uid) return;
  
  try {
    const userRef = doc(db, "users", uid);
    await updateDoc(userRef, {
      mealPlanProfile: {
        questionnaireCompleted: preferencesData.questionnaireCompleted || true, 
        allergies: preferencesData.allergies || [],
        excludedCuisines: preferencesData.excludedCuisines || [],
        // Provide safe fallback values for everything to prevent undefined crashes!
        goal: preferencesData.goal || "maintain", 
        monthlyBudget: preferencesData.monthlyBudget || 0,
        weight: preferencesData.currentWeight || 0, 
        version: 1, 
        meals: [], 
        completedAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      }
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
    const uploadedRecipeRefs = [];

    // Loop through the meals Gemini generated
    for (const recipeData of mealPlan) {
      
      // Process ingredients into References just like the Python script
      const processedIngredientItems = (recipeData.ingredientItems || []).map(item => ({
        ...item,
        ingredientRef: doc(db, "ingredients", item.ingredientId) 
      }));

      const firestoreDoc = {
        ...recipeData,
        // Ensure formatting matches your DB schema
        carbs: typeof recipeData.carbs === 'number' ? `${recipeData.carbs}g` : recipeData.carbs,
        fat: typeof recipeData.fat === 'number' ? `${recipeData.fat}g` : recipeData.fat,
        protein: typeof recipeData.protein === 'number' ? `${recipeData.protein}g` : recipeData.protein,
        difficulty: recipeData.difficulty?.charAt(0).toUpperCase() + recipeData.difficulty?.slice(1),
        ingredientItems: processedIngredientItems,
        ownerId: uid,
        updatedAt: serverTimestamp()
      };

      // 1. Save to the global 'recipes' collection
      const recipeRef = await addDoc(collection(db, "recipes"), firestoreDoc);
      uploadedRecipeRefs.push(recipeRef);
    }

    // 2. Link these new recipes to the user's profile array
    await updateDoc(userRef, {
      "mealPlanProfile.meals": arrayUnion(...uploadedRecipeRefs),
      "mealPlanProfile.updatedAt": serverTimestamp()
    });

    console.log("Gemini meal plan synced to Firestore!");
  } catch (error) {
    console.error("Error syncing Gemini plan:", error);
    throw error;
  }
};
