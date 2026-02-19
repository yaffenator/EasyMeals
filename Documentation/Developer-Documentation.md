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
- This folder handles all the backend functionality of our website, such as our data handling (and Firestore database connection) and the API communication with our AI model (Gemini).

## How to Build the Software:
1. Ensure that the code editor setup is completed by following all the steps from the "How to Obtain Source Code" section at the top.
2. Navigate to the frontend folder in your terminal.
3. Install the libraries through the terminal command "**npm i**" or "**npm install**."
4. Step 3 should take 30-60 seconds, depending on network speed. After it completes, verify that the packages.json file is not empty and has the downloaded dependencies and libraries.
5. While in the frontend directory, run the command "**npm run dev**."
6. There should be a local host IP in the terminal (typically "localhost:3000" unless it is being used by another background application). Ctrl-click on it to open it in your browser.
7. The software is now built, and the changes you make to the project should immediately appear in your local browser.

## How to Test the Software:

### Prerequisites

Before running tests, ensure the following:

- Python 3.10+ is installed
- A virtual environment is activated
- Backend dependencies are installed:
  - pip install -r requirements.txt **We haven't added a requirements.txt yet but plan to have one in the future**
- The .env file is configured correctly
- The Firestore service account key is located in the /secrets directory
- Internet access is available (required for Firestore and Gemini API interaction)

### Running the Test Suite

From the backend root directory, run:

**pytest**

This command will:

- Automatically discover all test files in the tests/ directory
- Execute all test cases
- Display pass/fail results in the terminal

To run a specific test file:

**pytest tests/test_ingredient_service.py**

Tests should not be executed directly using:

python test_file.py

### External Systems

Some tests may interact with external services such as Google Firestore.

To ensure tests run correctly:

- Firestore credentials must be valid
- The test environment should use a separate database (not production)

Future improvements will include mocking Firestore to prevent modification of live data during testing.

## How to Add New Tests:

### Test Location

All backend tests must be placed inside:

backend/tests/

Frontend tests must be placed inside:

frontend/tests/

### Naming Convention

All test files must follow this naming pattern:

test_<feature_name>.py

Examples:

test_ingredient_service.py
test_rating_service.py
test_meal_diversity.py

### Writing Test Functions

Each test function inside a test file must follow this pattern:

def test_<behavior_being_tested>():

Example:

def test_normalize_name_trims_whitespace():
    assert normalize_name("  Rice  ") == "rice"

### Test Harness

The backend uses **pytest** as its test harness.

Pytest automatically:

- Discovers test files
- Executes test cases
- Reports pass/fail results
- Provides debugging output

All tests should be run using:
**pytest**

Tests should **not** be executed directly using python test_file.py

## How to Build a Release of the Software:

### Pre-Release Steps

Before building a release, developers must:

1. Ensure all tests pass by running:
     **pytest**
2. Verify that:
  - Database seeding works correctly by runnning python3 seed_firestore.py and checking the database to ensure the database was seeded properly with the correct data.
  - Gemini integration functions properly
  - Rating service calculations are correct
3. Confirm that the .env file is configured for the production environment.
4. Update the version number in the codebase and documentation (if applicable).
