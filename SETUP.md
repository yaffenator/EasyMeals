# EasyMeals Setup and Deployment Guide

This document explains how a system administrator can install, configure, and deploy EasyMeals.

## 1. Architecture Overview

EasyMeals is a web application with separate services:

- Frontend: Next.js (`frontend/`)
- Backend API: FastAPI (`backend/`)
- Database/Auth/Storage: Firebase (Firestore + Authentication + Storage)
- AI provider: Google Gemini API

Important: the backend and frontend are started separately and deployed as separate services.

## 1.1 Hosting Architecture (Important)

EasyMeals is a hybrid deployment:

- Frontend hosting: can be deployed on Vercel (serverless-style Next.js hosting is supported).
- Backend hosting: must run as a separate persistent Python service (FastAPI + `uvicorn`) on a VM/container/app host.

This project is not a single fully serverless deployment. Do not deploy only the frontend and expect the app to work.

## 2. Required Accounts and Billing Plans

Before deployment, set up:

1. Google Cloud project with billing enabled
2. Firebase project linked to that Google Cloud project
3. Gemini API access in the same or linked Google Cloud context

Required paid tiers:

- Firebase must be on the Blaze (pay-as-you-go) plan.
- Gemini usage must be on a pay-as-you-go billing-enabled setup.

## 3. Software Prerequisites

Install on deployment hosts/build agents:

- Git
- Node.js 20+ and npm
- Python 3.10+ and pip
- (Optional) Python virtual environment support (`venv`)

## 4. Dependency Breakdown

### Backend libraries (full list used by this project)

From `backend/requirements.txt`:

- `fastapi`: Backend web framework for API routes
- `uvicorn`: ASGI server used to run FastAPI
- `firebase-admin`: Firebase Admin SDK for auth verification and admin operations
- `google-cloud-firestore`: Firestore database client library
- `google-cloud-storage`: Google Cloud Storage client (used by image-related workflows)
- `google-genai`: Gemini API client used for meal generation
- `python-dotenv`: Loads environment variables from `.env` files
- `pytest`: Backend test framework
- `pytest-cov`: Test coverage plugin for pytest

### Frontend libraries (most important)

The frontend has many transitive packages in `package-lock.json`; these are the key direct libraries administrators should know:

- `next`: Main frontend framework and runtime
- `react` and `react-dom`: UI rendering libraries used by Next.js
- `firebase`: Client SDK for Authentication and Firestore access in the UI
- `@google/generative-ai`: Gemini client used in frontend-side integration paths
- `tailwindcss`: Core styling framework used by the app
- `typescript`: Type-checked development/build tooling
- `jest` + `@testing-library/*`: Frontend testing stack

## 5. Get the Source Code

From your target machine:

```bash
git clone https://github.com/yaffenator/EasyMeals.git
cd EasyMeals
```

## 6. Configure Firebase and Gemini

In Firebase console:

1. Enable Firestore Database
2. Enable Firebase Authentication providers used by the app (Email/Password, Google, GitHub)
3. Ensure a Storage bucket exists
4. Create a service account key JSON (server-side use only)

In Google/Gemini setup:

1. Enable Gemini API access
2. Create an API key for server-side generation calls

## 7. Backend Setup (`backend/`)

### Install dependencies

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

### Required backend environment variables

- `FIREBASE_SERVICE_ACCOUNT` = full Firebase service account JSON as a single-line string
- `GEMINI_API_KEY` = Gemini API key

Optional tuning variables:

- `PLAN_GENERATION_MAX_WORKERS`
- `MEAL_DETAIL_PARALLELISM`
- `MEAL_DETAIL_SUBMIT_STAGGER_SECONDS`
- `GEMINI_CALL_TIMEOUT_SECONDS`
- `GEMINI_NAME_PASS_TIMEOUT_SECONDS`
- `GEMINI_RETRY_BACKOFF_SECONDS`

### Run backend locally

```bash
cd backend
uvicorn backend:app --host 0.0.0.0 --port 8000
```

Health check:

- `GET http://localhost:8000/health`

## 8. Frontend Setup (`frontend/`)

### Install dependencies

```bash
cd frontend
npm install
```

### Required frontend environment variables

- `NEXT_PUBLIC_BACKEND_API_URL` (example: `http://localhost:8000` in local dev)
- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
- `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
- `NEXT_PUBLIC_FIREBASE_APP_ID`

Optional:

- `NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID`
- `BACKEND_PROXY_TIMEOUT_MS`
- `PYTHON_BIN` (used by the image-generation route when needed)

### Run frontend locally

```bash
cd frontend
npm run dev
```

Default URL:

- `http://localhost:3000`

## 9. Start Order and Local Runtime

Run these in separate terminals/processes:

1. Backend API (`uvicorn ...` on port 8000)
2. Frontend Next.js server (`npm run dev` on port 3000)

Do not expect one command to start both services.

## 10. Deployment Model (Production)

Recommended:

1. Deploy backend (FastAPI) to a Python-capable host (VM/container/platform) and keep it running as a service
2. Deploy frontend (Next.js) to Vercel (or another Node.js-capable host)
3. Set frontend `NEXT_PUBLIC_BACKEND_API_URL` to the deployed backend HTTPS URL
4. Set all Firebase/Gemini secrets in each platform's secret manager (never commit secrets)

## 11. Post-Deployment Validation

1. Verify frontend loads and login works (Email/Password and OAuth providers)
2. Verify backend `/health` returns OK
3. Generate a meal plan and confirm Firestore writes under user collections
4. Verify Gemini-backed generation succeeds (no API-key/billing errors)
