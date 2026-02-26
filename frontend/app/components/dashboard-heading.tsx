"use client";

import { Leaf, LogOut, User } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function DashboardHeading() {
  const [hasAccount, setHasAccount] = useState(true);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Leaf className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl text-primary">EasyMeals</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            {/* <Link
              href="/how-it-works"
              className="text-foreground/80 hover:text-primary transition-colors"
            >
              How It Works
            </Link> */}
            <Link
              href="/dashboard"
              className="text-foreground/80 hover:text-primary transition-colors"
            >
              Dashboard
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/login">
              {hasAccount ? (
                /* Profile State */
                <button className="flex items-center gap-2 p-1.5 px-3 rounded-lg bg-primary hover:bg-primary/90 hover:cursor-pointer transition-all duration-200 text-primary-foreground">
                  <User className="h-5 w-5" />
                  <span className="bg-primary">My Profile</span>
                </button>
              ) : (
                /* Logged Out State */
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground transition-all duration-200">
                  <User className="h-5 w-5" />
                  <span>Create Account / Login</span>
                </button>
              )}
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
