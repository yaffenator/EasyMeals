import { DollarSign, Calendar, ShoppingCart, ChefHat } from 'lucide-react';

export function HowItWorks() {
  const steps = [
    {
      icon: DollarSign,
      title: "Set Your Budget",
      description: "Tell us how much you want to spend on groceries each week."
    },
    {
      icon: ChefHat,
      title: "Choose Preferences",
      description: "Select dietary preferences, allergies, and favorite cuisines."
    },
    {
      icon: Calendar,
      title: "Get Your Plan",
      description: "Receive a personalized weekly meal plan with recipes and portions."
    },
    {
      icon: ShoppingCart,
      title: "Shop & Cook",
      description: "Follow the auto-generated shopping list and start cooking!"
    }
  ];

  return (
    <section className="py-20 bg-white">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl mb-4">How EasyMeals Works</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Four simple steps to budget-friendly, delicious meals every week
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {steps.map((step, index) => (
            <div key={index} className="relative">
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <step.icon className="w-8 h-8 text-primary" />
                </div>
                <div className="absolute -top-2 -left-2 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center">
                  {index + 1}
                </div>
                <h3 className="text-xl">{step.title}</h3>
                <p className="text-muted-foreground">{step.description}</p>
              </div>
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-8 left-full w-full h-0.5 bg-gradient-to-r from-primary/30 to-transparent -translate-x-1/2"></div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
