"use client";

import { Leaf, LogOut, User } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginHeading() {
  const [hasAccount, setHasAccount] = useState(false);

  const router = useRouter();

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

          <div className="flex items-center gap-4">
            {hasAccount ? (
              <button
                className="p-2 rounded-lg bg-primary hover:bg-primary/90 hover:cursor-pointer transition-all duration-300 text-primary-foreground"
                onClick={() => router.push("/dashboard")}
              >
                Dashboard
              </button>
            ) : (
              <button
                className="p-2 rounded-lg bg-primary hover:bg-primary/90 hover:cursor-pointer transition-all duration-200 text-primary-foreground"
                onClick={() => router.push("/login")}
              >
                Create Account / Login
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
