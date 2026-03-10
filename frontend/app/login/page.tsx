"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import { ChefHat, Mail, Lock, User } from "lucide-react";
import { useRouter } from "next/navigation";
import LoginHeading from "../components/login-heading";
import {
  loginUser,
  registerUser,
  loginWithGoogle,
  loginWithGithub,
} from "../firebase";

export default function AuthPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const router = useRouter();

  // Handle basic email/password login with error handling for common Firebase Auth errors
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    console.log("loggin the user in...");
    setIsLoading(true);

    // Call the loginUser function and handle any errors
    try {
      await loginUser(email, password);
      // on successful login, redirect to dashboard
      router.push("/dashboard");
    } catch (err: any) {
      // Map Firebase error codes to user-friendly messages
      if (err.code === "auth/invalid-email") {
        setError("No user found with this email address.");
      } else if (err.code === "auth/wrong-password") {
        setError("Incorrect password. Please try again.");
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
      console.error("Error logging in user:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Google Sign-In with error handling for popup closure and cancellation
  const handleGoogleSignIn = async () => {
    setError(null);
    try {
      await loginWithGoogle();
      router.push("/dashboard");
    } catch (err: any) {
      if (err.code !== "auth/popup-closed-by-user") {
        setError("Failed to sign in with Google. Please try again.");
        console.error("Google sign-in error:", err);
      }
    }
  };

  // Handle GitHub Sign-In with error handling for popup closure and cancellation
  const handleGithubSignIn = async () => {
    setError(null);
    try {
      await loginWithGithub();
      router.push("/dashboard");
    } catch (err: any) {
      if (
        err.code !== "auth/popup-closed-by-user" &&
        err.code !== "auth/cancelled-popup-request"
      ) {
        setError("Failed to sign in with GitHub. Please try again.");
        console.error("GitHub sign-in error:", err);
      }
    }
  };

  // Handle user registration with email/password and error handling for common Firebase Auth errors
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    // check if both password fields match
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    console.log("registering user...");
    setIsLoading(true);

    // Call the registerUser function and handle any errors
    try {
      await registerUser(email, password, name);
      // on successful registration, redirect to dashboard
      router.push("/dashboard");
    } catch (err: any) {
      // Map Firebase error codes to user-friendly messages
      if (err.code === "auth/email-already-in-use") {
        setError("This email is already registered.");
      } else if (err.code === "auth/weak-password") {
        setError("Password is too weak. Please use at least 6 characters.");
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
      console.error("Error registering user:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white via-secondary/30 to-secondary/60">
      <LoginHeading />
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Logo and Branding */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-full mb-4">
              <ChefHat className="w-8 h-8 text-primary-foreground" />
            </div>
            <h1 className="text-3xl text-primary mb-2">Welcome to EasyMeals</h1>
            <p className="text-muted-foreground">
              Your personalized budget meal planning starts here
            </p>
          </div>

          {/* Auth Card */}
          <Card className="shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-primary text-2xl text-center">
                Get Started
              </CardTitle>
              <CardDescription className="text-center">
                Sign in or create a new account to access your personalized meal
                plans and recipes
              </CardDescription>
              <p className="text-sm text-center text-muted-foreground">
                Fields marked with <span className="text-red-800">*</span> are
                required
              </p>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="login" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-6">
                  <TabsTrigger value="login">Login</TabsTrigger>
                  <TabsTrigger value="signup">Sign Up</TabsTrigger>
                </TabsList>

                {/* Login Form */}
                <TabsContent value="login">
                  <form onSubmit={handleLogin} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="login-email">
                        Email<span className="text-red-800">*</span>
                      </Label>
                      <div className="relative">
                        <Mail className="absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="login-email"
                          type="email"
                          placeholder="you@example.com"
                          className="pl-10"
                          onChange={(e) => setEmail(e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    <div className="flex flex-col justify-center space-y-2">
                      <div>
                        <div className="flex items-center justify-between">
                          <Label htmlFor="login-password">
                            Password<span className="text-red-800">*</span>
                          </Label>
                        </div>
                        <div className="relative top-3">
                          <Lock className="absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
                          <Input
                            id="login-password"
                            type="password"
                            placeholder="••••••••"
                            className="pl-10"
                            onChange={(e) => setPassword(e.target.value)}
                            minLength={6}
                            required
                          />
                        </div>
                      </div>
                    </div>

                    {error && (
                      <div className="p-3 text-sm text-white bg-red-600 rounded-md text-center">
                        {error}
                      </div>
                    )}

                    <button
                      type="submit"
                      className="w-full bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg mt-3 p-2 hover:cursor-pointer transition-all duration-200"
                      disabled={isLoading}
                    >
                      {isLoading ? "Signing in..." : "Sign In"}
                    </button>
                  </form>
                </TabsContent>

                {/* Signup Form */}
                <TabsContent value="signup">
                  <form onSubmit={handleSignup} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="signup-name">
                        Full Name<span className="text-red-800">*</span>
                      </Label>
                      <div className="relative">
                        <User className="absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="signup-name"
                          type="text"
                          placeholder="John Doe"
                          className="pl-10"
                          onChange={(e) => setName(e.target.value)}
                          maxLength={25}
                          pattern="[A-Za-z\s]+"
                          required
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="signup-email">
                        Email<span className="text-red-800">*</span>
                      </Label>
                      <div className="relative">
                        <Mail className="absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="signup-email"
                          type="email"
                          placeholder="you@example.com"
                          className="pl-10"
                          onChange={(e) => setEmail(e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="signup-password">
                        Password<span className="text-red-800">*</span>
                      </Label>
                      <div className="relative">
                        <Lock className="absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="signup-password"
                          type="password"
                          placeholder="••••••••"
                          className="pl-10"
                          onChange={(e) => setPassword(e.target.value)}
                          minLength={6}
                          required
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Must be at least 6 characters
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="signup-confirm-password">
                        Confirm Password<span className="text-red-800">*</span>
                      </Label>
                      <div className="relative">
                        <Lock className="absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="signup-confirm-password"
                          type="password"
                          placeholder="••••••••"
                          className="pl-10"
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          minLength={6}
                          required
                        />
                      </div>
                    </div>

                    {error && (
                      <div className="p-3 text-sm text-white bg-red-600 rounded-md text-center">
                        {error}
                      </div>
                    )}

                    <button
                      type="submit"
                      className="w-full bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg p-2 hover:cursor-pointer transition-all duration-200"
                      disabled={isLoading}
                    >
                      {isLoading ? "Creating account..." : "Create Account"}
                    </button>
                  </form>
                </TabsContent>
              </Tabs>

              {/* Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-400"></div>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">
                    Or continue with
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Google OAuth Login Button */}
                <button
                  className="flex items-center justify-center bg-green-50 rounded-lg p-2 hover:bg-green-100 hover:cursor-pointer transition-colors duration-200"
                  type="button"
                  disabled={isLoading}
                  onClick={handleGoogleSignIn}
                >
                  <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                    <path
                      fill="currentColor"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="currentColor"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="currentColor"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="currentColor"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  Google
                </button>

                {/* GitHub OAuth Login Button */}

                <button
                  className="flex items-center justify-center bg-green-50 rounded-lg p-2 hover:bg-green-100 hover:cursor-pointer transition-colors duration-200"
                  type="button"
                  disabled={isLoading}
                  onClick={handleGithubSignIn}
                >
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                  GitHub
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
