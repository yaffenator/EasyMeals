import { Heart, TrendingUp, Users } from "lucide-react";

export function OurMission() {
  return (
    <section className="py-20 bg-gradient-to-b from-white to-secondary/30">
      <div className="container mx-auto px-4">
        <div className="max-w-4xl mx-auto text-center mb-12">
          <h2 className="text-3xl md:text-4xl text-primary mb-6">
            Our Mission
          </h2>
          <p className="text-lg leading-relaxed text-foreground/90">
            <strong className="text-primary">Meal prepping is hard. </strong>
            For anyone receiving food benefits or other financial aid,
            allocating such income to effectively may seem like a daunting task.
            At <strong className="text-primary">EasyMeals</strong>, we're
            committed to{" "}
            <strong className="text-primary">fighting food insecurity</strong>{" "}
            by empowering people to make the most of their grocery budget. We
            believe everyone deserves access to healthy, fitness-driven,
            gratifying meals regardless of their financial situation.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-primary/10 text-center hover:cursor-pointer hover:shadow-lg transition-shadow duration-300">
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Heart className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl text-primary mb-3">Accessible Nutrition</h3>
            <p className="text-foreground/80">
              Everyone deserves healthy meals that align with their fitness
              goals. We make nutritious eating achievable for any budget.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border border-primary/10 text-center hover:cursor-pointer hover:shadow-lg transition-shadow duration-300">
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl text-primary mb-3">Maximize Your Budget</h3>
            <p className="text-foreground/80">
              Our personalized plans help you get the most value from every
              dollar spent on groceries, and recommends meals that you'll love.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border border-primary/10 text-center hover:cursor-pointer hover:shadow-lg transition-shadow duration-300">
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl text-primary mb-3">
              Empowering Communities
            </h3>
            <p className="text-foreground/80">
              Together, we're building a future where budget never stands
              between you and good food.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
