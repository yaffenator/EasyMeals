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
          <p className="text-lg text-primary-foreground/90">
            Join thousands of families who are eating better and spending less.
            Get your first week's meal plan free.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
            <button
              className="bg-white text-primary hover:bg-white/90 flex"
              onClick={() => router.push("/dashboard")}
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
