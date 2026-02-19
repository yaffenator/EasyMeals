# User Documentation

## Description:

EasyMeals allows users to make an account and generate a monthly meal plan based on their preferences, food restrictions, health goals, and budget. We take the stress and time out of planning and research, and allow our software to make meal plans generated towards you. Users use our software  to go from having no knowledge of meal planning, or not knowing how to utilize their budget well, to having all the tools and resources needed to successfully meal plan, specifically for them. 

## How to Install

*Currently, this website is hosted locally, so there is no public domain to people to access it at. If it was, there wouldn't be a need to install anything. Here are the steps to download its libraries for local hosting:*
1. Clone the github repo into your IDE. -*Our group has used VS code for the project*-
2. Navigate to the frontend folder in your terminal
3. Install the libraries through the terminal command "**npm i**" or "**npm install**"
4. Step 3 sholuld take 30-60 seconds depending on network speed. After it completes, verify the packages.json file is not empty and has the downloaded dependencies and libraries

## How to Run

*Currently, this website is hosted locally, so there is no public domain to people to access it at. If it was, you would look up the domain on any browser. Here are the steps to run it for local hosting:*
1. Ensure all dependencies are installed by following steps 1-4 in "How to Install"
2. While in the frontend directory, run the command "**npm run dev**"
3. There should be a local host IP in the terminal, ctrl click on it to open it in your browser

## How to Use

*Our website does not currently have user authnetication but will by the time it is due*
1. If you don't already have an account, make one with the sign-up button in the top right; otherwise, log in with your credentials. NOTE: Our authentication system isn't currently up-to-date, so you can skip this step and go to "localhost:3000/dashboard" to view the dashboard without logging in.
2. Navigate to the dashboard page at the top of the screen.
3. Press the "**Generate Meal Plan**" button to get started.
4. Follow the prompts to continue to generate your meals based on your preferences.
5. Look over each meal and make sure it doen't conflits with your preferneces
6. Refesh any unwanted, or conflicting meals -*Awaiting Implementation*-
7. Get cooking!

## How to Report a Bug
To report a bug, fill out the bug form found on the footer of our website.

When reporting a bug, please include enough detail so that we may reproduce it quickly:

1. **Where it happened**
   - Page/URL (example: `/dashboard`)
   - What button/action you clicked (example: “Generate Meal Plan”)

2. **What you expected vs. what actually happened**
   - Example:
     - Expected: “Meal plan loads in the dashboard”
     - Actual: “Spinner never stops / error message appears”

4. **Steps to reproduce (numbered)**
   - Example:
     1. Open `/dashboard`
     2. Click **Generate Meal Plan**
     3. Enter budget = 200, gluten-free = true
     4. Submit

5. **Logs + screenshots**
   - Screenshot of the error (if applicable)
   - **Frontend logs:** Press F12 inside the browser to access the DevTools console
   - **Backend logs:** If locally hosting, provide a screenshot of the terminal
   - Include the full error text (copy/paste)

6. **Environment info**
   - If hosting locally please provide:
     - OS (Windows/Mac/Linux)
     - Node version (`node -v`)
     - Python version (`python --version`)
     - Whether you’re running locally and which branch/commit (if known)
   - If running through hosted website, please provide the Browser you are currently on.



## Known Bugs
Because EasyMeals is still under early active development, there are no known bugs due to the lack of implementation and features. As development progresses, known bugs will be recorded in GitHub issues and listed here.
