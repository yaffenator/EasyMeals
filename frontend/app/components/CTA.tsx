"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Input } from "./ui/input";

export function CTA() {
  const router = useRouter();

  return (
    <section className="py-20 bg-gradient-to-br from-primary to-primary/80 text-primary-foreground">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <h2 className="text-3xl md:text-4xl">Ready to Start Saving?</h2>
          <p>
            Your personalized, budget-friendly meal plan is just a click away.
          </p>
          <div className="flex justify-center items-center sm:flex-row gap-4 max-w-md mx-auto">
            <button
              className="p-2 bg-white text-primary hover:bg-white/90 hover:cursor-pointer transition-all duration-300 flex rounded-lg"
              onClick={() => router.push("/login")}
            >
              Get Started for Completely Free!
              <ArrowRight className="ml-2 h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
