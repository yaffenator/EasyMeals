# EasyMeals

**EasyMeals** automates your meal-prepping goals with a personalized AI nutrition expert. Whether you are managing food benefits, sticking to a strict budget, or pursuing specific fitness goals, EasyMeals creates a comprehensive, month-long plan tailored to your wallet and your health.

---

##  Team Information

| Name | Role |
| :--- | :--- |
| **Dylan Peniuk** | Project Leader |
| **Ayowade Owojori** | Backend Lead |
| **Noam Yaffe** | Frontend Lead |
| **Dean Leon** | Full-stack Developer |

* **GitHub Repository:** [https://github.com/yaffenator/EasyMeals](https://github.com/yaffenator/EasyMeals)
* **Communication:** Microsoft Teams

---

##  Product Description

### Abstract
Meal prepping is hard, especially for individuals receiving food benefits or financial aid. Properly allocating a monthly income to groceries efficiently can be a daunting task. EasyMeals allows you to enter your monthly food budget and physical goals (e.g., losing weight or building muscle). Using this data, EasyMeals generates a month-long meal plan, including specific grocery lists and fun, satisfying recipes.

### Goal
The goal of this project is to allow people to skip the trouble of budgeting and the stress of finding recipes by having it all in one place. It will automatically provide a list of groceries and recipes week-by-week, while factoring in allergies and restrictions to ensure a stress-free experience.

### Current Practice
Today, services like *HelloFresh* or *Factor_* provide meal plans, but they are often expensive, use subscription models that don't accept EBT/food stamps, and remove the transparency of where food is sourced.

### Novelty
Our approach uses an **AI assistant** to web-scrape products from local grocery stores. This factors in real-time pricing—a feature absent from most competitors—and allows users to cook the meals themselves rather than receiving pre-packaged shipments.

---

##  Major Features (MVP)

* **Budget-Optimized Grocery Lists:** A weekly grocery list that stays strictly within the user's defined budget.
* **Monthly Recipe Rotation:** A full month of recipes for meals the user can cook at home.
* **Goal-Oriented Nutrition:** Meals specifically targeted toward fitness goals (e.g., building muscle or weight loss).
* **Allergy & Restriction Filtering:** Allows users to add food restrictions to prevent allergic reactions.

###  Stretch Goals
* **Family Scaling:** Allow users to add family members to their meal plan (e.g., prepping for a family of 4).
* **Store Customization:** Allow a selection of specific nearby grocery stores to purchase from.

---

##  Technical Approach

EasyMeals is built using a modern, scalable stack designed for performance and security.

* **Frontend:** React with Next.js framework (leveraging server-side rendering and code splitting).
* **Styling:** TailwindCSS for responsive design.
* **Languages:** TypeScript for the frontend and Python for backend functions.
* **AI/LLM:** Fine-tuned AI model implemented via a Gemini API handler.
* **Database:** MongoDB (or Firebase/Supabase) to store user preferences.
* **Authentication:** Basic email/password and OAuth (Google).

---

##  Risks

* **Pricing Accuracy:** Finding accurate food prices to ensure users do not go over budget.
* **Safety & Liability:** Ensuring strict exclusion of flagged food restrictions to prevent allergic reactions.
* **Data Privacy:** Securing sensitive user data such as weight, lifestyle, and health metrics.
