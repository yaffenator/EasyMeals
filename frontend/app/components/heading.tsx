"use client";

import { Leaf, LogOut, User } from "lucide-react";
import { useState } from "react";
import { Link as ScrollLink } from "react-scroll";
import Link from "next/link";

export default function Heading() {
  const [hasAccount, setHasAccount] = useState(false);

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
            <ScrollLink
              to="home" // The ID of the target element
              smooth={true} // Enable smooth scrolling
              duration={500} // Scroll duration in milliseconds
              spy={true} // Enable scrollspy (highlights the link when target is active)
              activeClass="active-link" // CSS class to apply when active
              offset={-70} // Adjust scroll position (e.g., for fixed headers)
              className="hover:cursor-pointer hover:text-primary transition-all duration-200"
            >
              Home
            </ScrollLink>
            <ScrollLink
              to="our-mission" // The ID of the target element
              smooth={true} // Enable smooth scrolling
              duration={500} // Scroll duration in milliseconds
              spy={true} // Enable scrollspy (highlights the link when target is active)
              activeClass="active-link" // CSS class to apply when active
              offset={-70} // Adjust scroll position (e.g., for fixed headers)
              className="hover:cursor-pointer hover:text-primary transition-all duration-200"
            >
              Our Mission
            </ScrollLink>
            <ScrollLink
              to="how-it-works"
              smooth={true}
              duration={500}
              spy={true}
              activeClass="active-link"
              offset={-70}
              className="hover:cursor-pointer hover:text-primary transition-all duration-200"
            >
              How it Works
            </ScrollLink>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/signin" className="no-style-link">
              {hasAccount ? (
                <button className="p-2 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground">
                  Dashboard
                </button>
              ) : (
                <button className="p-2 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground">
                  Create Account / Login
                </button>
              )}
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
