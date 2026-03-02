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

// initialize firebase app and auth
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// create google and github auth providers
const googleProvider = new GoogleAuthProvider();
const githubProvider = new GithubAuthProvider();

// email password registration function that takes in an email, password, and name and returns the user if the registration is successful, otherwise throws an error
export const registerUser = async (email, password, name) => {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(userCredential.user, { displayName: name });
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
    return userCredential.user;
  } catch (error) {
    throw error;
  }
}

// github sign in function that uses the GithubAuthProvider to sign in with a popup and returns the user if the login is successful, otherwise throws an error
export const loginWithGithub = async () => {
  try {
    const userCredential = await signInWithPopup(auth, githubProvider);
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