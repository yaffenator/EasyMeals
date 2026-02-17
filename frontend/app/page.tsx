"use client";

import Heading from "./components/heading";
import { Hero } from "./components/hero";
import { OurMission } from "./components/ourMission";
import { HowItWorks } from "./components/howItWorks";
import { Features } from "./components/features";
import { CTA } from "./components/CTA";
import { Footer } from "./components/footer";
import { Element } from "react-scroll";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Heading />
      <main>
        <Element name="home" className="">
          <Hero />
        </Element>
        <Element name="our-mission" className="">
          <OurMission />
        </Element>
        <Element name="how-it-works" className="">
          <HowItWorks />
        </Element>
        <Element name="features" className="">
          <Features />
        </Element>
        <CTA />
      </main>
    </div>
  );
}
