# Deployment Guide

This application is containerized using Docker and is ready for deployment on platforms like **Railway** or **Render**.

## Option 1: Railway (Recommended)

Railway is excellent for Docker-based projects and handles Playwright dependencies well.

### Steps:
1.  **Sign Up/Login**: Go to [railway.app](https://railway.app/) and login with GitHub.
2.  **New Project**: Click "New Project" -> "Deploy from GitHub repo".
3.  **Select Repository**: Choose `askar0007amirkhanov/ai-precheck`.
4.  **Add Variables**:
    *   Click on the new service card.
    *   Go to the **Variables** tab.
    *   Add your secrets:
        *   `OPENAI_API_KEY`: `sk-...` (your real key)
        *   `GEMINI_API_KEY`: (optional)
        *   `Environment`: `production`
5.  **Deploy**: Railway will automatically build the Docker image and deploy it.
6.  **Verify**: Click the generated URL provided by Railway.

> **Note on Playwright**: The Dockerfile installs Playwright browsers automatically during the build process.

## Option 2: Render

Render is also a great option but the free tier spins down after inactivity.

### Steps:
1.  **Sign Up/Login**: Go to [render.com](https://render.com/).
2.  **New Web Service**: Click "New +" -> "Web Service".
3.  **Connect Repo**: Select `ai-precheck`.
4.  **Runtime**: Select **Docker**.
5.  **Environment Variables**:
    *   Add `OPENAI_API_KEY`.
    *   Add `PORT`: `8000` (Render explicitly looks for this).
6.  **Create Web Service**: Click the button to start deployment.

## Important Notes

*   **Mock Functionality**: If you do not provide a valid `OPENAI_API_KEY`, the application will continue to work in "Mock Mode" (returning demo data), just like it did locally.
*   **Database**: By default, this app uses SQLite (`compliance.db`). In a real production setup on these platforms, the file system is ephemeral (changes are lost on restart).
    *   **For Demo**: This is fine (data resets on deploy).
    *   **For Real Use**: You should provision a PostgreSQL database (Railway provides one in one click) and set `DATABASE_URL` env var.
