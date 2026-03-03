# EasyMeals

**EasyMeals** automates your meal-prepping goals with a personalized AI nutrition expert. Whether you are managing food benefits, sticking to a strict budget, or pursuing specific fitness goals, EasyMeals creates a comprehensive, month-long plan tailored to your wallet and your health.

---

## Working Use Cases (For In-Class BETA Testing)

* **Use Case #1:** The user will be able to create an account & log into it successfully through 1. Email/Password Verification, 2. Personal Google Account (OAuth), 3. Personal GitHub Account (OAuth)
* **Use Case #2:** The registered user will narrow down their health requirements & fitness goals through a variety of health-related inquiries.
* **Use Case #3:**  Upon completing the health requirements & fitness goals questionnaire, the registered user will receive an itemized list of groceries and curated recipes tailored specifically to their financial constraints and physical objectives.

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
Meal prepping is hard. For any individual receiving food benefits or other financial aid, the idea of properly allocating a portion of their monthly income to groceries as effectively and efficiently as possible may seem like a daunting task. Introducing: EasyMeals – Automate your meal-prepping goals with a personalized AI nutrition expert. This website will allow you to enter the amount of money you allocate to food and groceries each month and select your physical goals (such as losing weight or building muscle) and their extent. Using this information, EasyMeals will create a month-long meal-prepping plan, showing you what groceries to buy, how much of each grocery item you will need, and some fun meals that you can prepare to satisfy your hunger.

### Goal
The goal of this project is to make a website that allows people to skip the trouble of budgeting for food and the stress of finding recipes to prepare, by having it all in one place. It will allow people to enter their monthly food budget and automatically give a list of groceries to buy and recipes of what to cook week by week. It will also ask for food allergies and restrictions to let people be stress-free about what they are eating. Overall, this project would reduce the stress of wondering what you are able to afford and what you are able to make, by laying it all out month by month.

### Current Practice
Today, services like *HelloFresh* or *Factor_* provide meal plans, but they are often expensive, use subscription models that don't accept EBT/food stamps, and remove the transparency of where food is sourced.

### Novelty
What makes our approach different is the introduction of an **AI assistant** that will webscrape products from local grocery stores to create specialized meal plans that are applicable to user requests. This approach will factor in the price of the ingredients, which is absent from existing services, and the ability to cook the meals yourself, where services like Factor_ ship the entire meal.

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
