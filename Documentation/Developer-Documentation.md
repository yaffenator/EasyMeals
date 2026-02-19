# Developer Documentation

## How to Obtain Source Code:

- To obtain the source code on your local machine, clone our GitHub repository into a new directory on a code editor like VSCode. This is done by going to our EasyMeals GitHub repository --> clicking the "<> Code" button at the top right --> navigating to the "HTTPS" clone selection --> copying the provided GitHub web URL --> entering the command "git clone [provided web URL]" into your code editor in the new directory. You should be all set now!
- The source code can also be downloaded via a downloaded Zip file of our GitHub repository. This Zip file can then be decompressed and uploaded (dragged & dropped) into VSCode or another code editor.

## Layout of Directory Structure:

The layout of our repository is split between two folders:

**Frontend:**
- This folder handles and renders the different pages on our website, their specific UI/UX components, and their routing.
- The "app" folder contains a variety of different sub-folders, each listed below:
    - The "components" subfolder contains all the general UI components used across our web pages, which are separated into page-specific components (like the "HowItWorks.tsx" component) and generalized components (like          the "checkbox.tsx" component) that are stored in the "ui" subfolder.
    - The "utils" subfolder is used to store small, reusable helper functions and snippets of code that perform generic tasks but don't belong to any specific feature or component. These include functions like the meal           generation function and others used in our project.
    - All other subfolders in "app" represent a different page in our application (for example, the "dashboard" page or the "login" page). This is because Next.js handles routing through a file-system-based approach, where       the folder and file structure in the dedicated app directory automatically defines the application's routes. Each of these route-defining subfolders contains a "page.tsx" file that renders the content displayed on           their page in the website.
- The "public" folder contains different .png and .svg files that are used globally across the project frontend.

**Backend:**
- [...]

## How to Build the Software:
1. Ensure all dependencies are installed by following steps 1-4 in "How to Install"
2. While in the frontend directory, run the command "**npm run dev**"
3. There should be a local host IP in the terminal (typically "localhost:3000" unless it is being used by another background application). Ctrl-click on it to open it in your browser
4. The software is now built, and the changes you make to the project should immediately appear in your local browser

## How to Test the Software:

TEXT HERE

## How to Add New Tests:

TEXT HERE

## How to Build a Release of the Software:

TEXT HERE
