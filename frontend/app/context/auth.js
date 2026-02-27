"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../firebase";

// create an auth context that will be used to provide the current user to the rest of the app
export const AuthContext = createContext({
    currentUser: null,
});

export const useAuth = () => {
    return useContext(AuthContext);
};

// auth context provider component that listens for auth state changes and provides the current user to its children
export const AuthProvider = ({ children }) => {
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        onAuthStateChanged(auth, user => {
            // if the user is logged in, set the current user to the user's email and display name, otherwise set it to null
            if (user) {
                setCurrentUser({
                    email: user.email,
                    displayName: user.displayName,
                });
            }
            else {
                setCurrentUser(null);
            }
        });
    }, []);

    // provide the current user to the children components
    return (
        <AuthContext.Provider value={{ currentUser }}>
            {children}
        </AuthContext.Provider>
    )
}