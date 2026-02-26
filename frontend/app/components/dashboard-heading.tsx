"use client";

import { ArrowRight, Leaf, LogOut, User } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { logoutUser } from "../firebase";

export default function DashboardHeading() {
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
            {/* <Link
              href="/dashboard"
              className="text-foreground/80 hover:text-primary transition-colors"
            >
              Dashboard
            </Link> */}
          </nav>

          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                logoutUser();
              }}
              className="flex items-center gap-1 py-2 px-4 rounded-lg bg-primary hover:bg-primary/90 hover:cursor-pointer transition-all duration-200 text-primary-foreground"
            >
              Sign Out
              <ArrowRight className="w-5 h-5 text-primary-foreground" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
