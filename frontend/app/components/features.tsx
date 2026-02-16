import { Check } from "lucide-react";
import ImageWithFallback from "./Figma/imageWithFallback";

export function Features() {
  const benefits = [
    "Reduce food waste with precise portions",
    "Discover new recipes every week",
    "Automatic nutritional information",
    "Flexible meal swaps and substitutions",
    "Print-friendly shopping lists",
    "Budget tracking and insights",
  ];

  return (
    <section className="py-20 bg-secondary">
      <div className="container mx-auto px-4">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="order-2 lg:order-1">
            <div className="relative rounded-2xl overflow-hidden shadow-xl">
              {/* <ImageWithFallback
                src="https://images.unsplash.com/photo-1576089073624-b5751a8f4de9?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxmYW1pbHklMjBlYXRpbmclMjBkaW5uZXIlMjB0b2dldGhlcnxlbnwxfHx8fDE3Njk3NTEwODJ8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                alt="Family enjoying a meal together"
                className="w-full h-auto"
              /> */}
              <h1>placeholder</h1>
            </div>
          </div>

          <div className="space-y-6 order-1 lg:order-2">
            <h2 className="text-3xl md:text-4xl">More Than Just Meal Plans</h2>
            <p className="text-lg text-muted-foreground">
              EasyMeals helps you take control of your food budget without
              sacrificing quality or flavor. Our smart algorithm considers
              seasonal ingredients and local prices to maximize your savings.
            </p>

            <div className="grid sm:grid-cols-2 gap-4">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Check className="w-3 h-3 text-primary-foreground" />
                  </div>
                  <span className="text-foreground">{benefit}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
