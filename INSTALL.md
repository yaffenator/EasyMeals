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
