import { initializeApp } from "firebase/app";
import { 
  getAuth, 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  updateProfile 
} from "firebase/auth";

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

export const registerUser = async (email, password, name) => {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(userCredential.user, { displayName: name });
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

export const loginUser = async (email, password) => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

export const logoutUser = async () => {
  try {
    await auth.signOut();
  } catch (error) {
    throw error;
  }
}