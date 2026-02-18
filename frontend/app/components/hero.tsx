"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import ImageWithFallback from "./Figma/imageWithFallback";
import Typewriter from "typewriter-effect";

export function Hero() {
  const router = useRouter();

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-white to-secondary py-20 md:py-32">
      <div className="container mx-auto px-4">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <div className="inline-block px-4 py-2 bg-accent rounded-full">
              <span className="text-accent-foreground">
                Smart Meal Planning Made Simple
              </span>
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl">
              Plan Out Delicious Meals That Fit Your{" "}
              <span className="text-primary inline-block">
                <Typewriter
                  // tag="span"
                  options={{
                    wrapperClassName: "ah-words-wrapper",
                    strings: ["Budget", "Health Goals"],
                    autoStart: true,
                    loop: true,
                  }}
                />
              </span>
            </h1>
            <p className="text-lg text-muted-foreground">
              Get personalized weekly meal plans tailored to your monthly food
              benefit and fitness goals. Save money, eat healthier, and never
              wonder "what's for dinner?" again.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center p-2 rounded-lg"
                onClick={() => router.push("/dashboard")}
              >
                Get Started
                <ArrowRight className="ml-2 h-5 w-5" />
              </button>
            </div>
          </div>
          <div className="relative">
            <div className="absolute -top-4 -right-4 w-72 h-72 bg-primary/10 rounded-full blur-3xl"></div>
            <div className="relative rounded-2xl overflow-hidden shadow-2xl">
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1606859191214-25806e8e2423?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxmcmVzaCUyMGhlYWx0aHklMjB2ZWdldGFibGVzJTIwbWVhbCUyMHByZXB8ZW58MXx8fHwxNzY5NzUxMDgxfDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                alt="Fresh healthy meal preparation"
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
