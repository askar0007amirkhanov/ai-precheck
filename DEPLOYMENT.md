# Deployment Guide

## Railway (Recommended)

1. **Sign Up/Login**: Go to [railway.app](https://railway.app/) and login with GitHub.
2. **New Project**: Click "New Project" → "Deploy from GitHub repo".
3. **Select Repository**: Choose your `ai-precheck` repo.
4. **Add Variables** (in the Variables tab):
   - `LLM_PROVIDER`: `mock` (for demo) or `openai`/`gemini` (with real keys)
   - `OPENAI_API_KEY`: your OpenAI key (if using OpenAI)
   - `GEMINI_API_KEY`: your Gemini key (if using Gemini)
   - `ALLOWED_ORIGINS`: your Railway domain (e.g., `https://your-app.up.railway.app`)
   - `ENVIRONMENT`: `production`
5. **Deploy**: Railway will build from the Dockerfile and start automatically.
6. **Verify**: Visit the generated URL → `/health` should return `{"status": "ok", ...}`

> **Note**: Database tables are created automatically on startup. The app uses SQLite by default — data persists across restarts on Railway but is reset on new deploys. For persistent data, switch to an external database (see below).

## Render

1. **Sign Up/Login**: Go to [render.com](https://render.com/).
2. **New Web Service**: Click "New +" → "Web Service".
3. **Connect Repo**: Select `ai-precheck`.
4. **Runtime**: Select **Docker**.
5. **Environment Variables**: Same as Railway (above).
6. **Create Web Service**: Deploy.

## Future: PostgreSQL / Supabase

To switch from SQLite to PostgreSQL (e.g., Supabase free tier):

1. Get a Supabase connection string (Transaction pooler, port 6543)
2. Set `DATABASE_URL=postgresql+asyncpg://user:pass@host:6543/postgres`
3. Redeploy — tables will be auto-created

## Important Notes

- **Mock Mode**: Without valid API keys, the app works in mock mode (returns demo compliance data). Set `LLM_PROVIDER=mock` explicitly.
- **Playwright**: The Dockerfile installs Chromium automatically. No extra setup needed.
- **Database**: SQLite is fine for single-instance deployment. For multi-instance or persistent data, use PostgreSQL.
