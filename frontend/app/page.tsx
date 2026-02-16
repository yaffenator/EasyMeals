import Heading from "./components/heading";
import { Hero } from "./components/hero";
import { OurMission } from "./components/ourMission";
import { HowItWorks } from "./components/howItWorks";
import { Features } from "./components/features";
import { CTA } from "./components/CTA";
import { Footer } from "./components/footer";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Heading />
      <main>
        <Hero />
        <OurMission />
        <HowItWorks />
        <Features />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
