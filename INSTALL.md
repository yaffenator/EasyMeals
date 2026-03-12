# EasyMeals Installation & Setup Guide

Welcome to **EasyMeals**, an AI-powered meal planning application for EBT receivers that helps you hit your fitness goals while staying under budget. This document provides step-by-step instructions to get the application running on your local machine or access the live version.

## Live Application
The application is fully deployed and can be accessed without any local setup.
* **URL:** [https://easy-meals-nine.vercel.app/](https://easy-meals-nine.vercel.app/)

---

## Local Development Setup

To run this project locally, you will need to set up both the **Next.js Frontend** and the **FastAPI Backend**.

### 1. Prerequisites
Ensure you have the following installed:
* **Node.js** (v18+)
* **Python** (v3.9+)
* **Git**
* **Firebase Project:** You will need a Firebase project with Authentication, Firestore, and Storage enabled.

### 2. Repository Structure
```text
/root
  ├── frontend/   # Next.js Application
  └── backend/    # FastAPI Python Server
```
### 3. Backend Setup (Python & FastAPI)
The backend handles AI meal generation (Gemini), image processing, and secure database interactions.
* Navigate to the backend directory: **cd backend**
* Install dependencies: **pip install -r requirements.txt**
* Firebase credentials: Generate a New Private Key from your Firebase Console (**Project Settings > Service Accounts**). Save this file as **serviceAccountKey.json** inside a folder named **secrets/** at the root of the backend directory.
* Create a new **.env** file in the backend/ folder, and put the following information into it:
```
GEMINI_API_KEY=your_google_gemini_api_key
NEXT_PUBLIC_storageBucket=your-project-id.appspot.com
```
* Start the server: **uvicorn backend:app --reload --port 8000** (The backend will be live at http://127.0.0.1:8000)

### 4. Frontend Setup (Next.js)
The frontend provides the user with the website's various UI.
* Navigate to the frontend directory: **cd frontend**
* Install dependencies: **npm install**
* Create a **.env.local** file in the frontend/ folder, and put the following information into it:
```
NEXT_PUBLIC_apiKey=your_firebase_api_key
NEXT_PUBLIC_authDomain=your_project.firebaseapp.com
NEXT_PUBLIC_projectId=your_project_id
NEXT_PUBLIC_storageBucket=your_project.appspot.com
NEXT_PUBLIC_BACKEND_API_URL=[http://127.0.0.1:8000]
```
* Run the application: **npm run dev**

You can now access the app at **http://localhost:3000**!

---

### How to Use

1. **Login:** Create an account using the Login page.
2. **The Questionnaire:** If you don't have a plan, you will be redirected to the meal plan questionnaire.
3. **Personalizations:** Set your budget (e.g., $400), your current weights (in lbs), your health goal (Lose, Maintain, or Gain weight), and any allergies/cuisines to avoid.
4. **Generate:** Click Finish & Generate. The AI (Gemini) will construct a 4-week meal plan.
5. **Review:** Once generated, browse your meals, view detailed recipes, and track your total caloric intake and budget spend.
