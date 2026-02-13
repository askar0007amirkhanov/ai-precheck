# AI Compliance & Onboarding Agent

## 1. Project Context
**Goal**: Build a scalable, modular monolith backend for a Fintech AI Compliance & Onboarding system.
**Core Value**: Automated website readiness checks for receiving payments (KYC/AML compliance) and a dynamic policy widget for clients.

## 2. Architecture: "Modular Monolith" aka Smart Scale MVP
The codebase is structured as a Modular Monolith. 
- **Core**: Shared infrastructure (DB, Config, Logging).
- **Modules**: Loose coupling between domains (`compliance`, `onboarding`, `policies`).
- **AI Layer**: Abstracted LLM access. No hard dependency on a specific provider.
- **Data Acquisition**: Playwright Crawler (running in Docker/Sandboxed).

### Tech Stack
-   **Runtime**: Python 3.11
-   **Framework**: FastAPI (Async)
-   **Database**: 
    -   *Local/Demo*: SQLite + aiosqlite
    -   *Production*: PostgreSQL 16 (Async)
-   **ORM**: SQLAlchemy 2.0
-   **Async Tasks**: Redis + ARQ (for long-running crawls)
-   **Browser**: Playwright

## 3. Current Status (as of 2026-02-12)

### ✅ Implemented Features
-   **Project Skeleton**: FastAPI app, folder structure, config management.
-   **AI Abstraction**: `LLMFactory` supporting OpenAI & Gemini (Mocked integration).
-   **Rule Engine**: Deterministic Python-based compliance logic (No LLM hallucinations for rules).
-   **Crawler**: Playwright integration (Mocked in tests).
-   **Dynamic Policy Widget**: 
    -   Database Schema (`PolicyTemplate`, `ClientWidget`).
    -   "Shadow DOM" JS Widget architecture.
    -   Seeding script (`seed_data.py`).
-   **Reporting**: PDF Report generation (`WeasyPrint`).
-   **Demo**: `index.html` UI + `seed_data.py` for quick start.

### 🚧 Works In Progress / Next Steps
-   **Deployment**: Moving from local dev to a hosted environment.
-   **Real Integration**: Connecting real OpenAI/Gemini keys.
-   **Production DB**: Switching from SQLite to Postgres.

## 4. Setup & Run

### Prerequisites
- Python 3.11+
- (Optional) Docker for Production

### Quick Start (Local Demo)
1.  **Install Dependencies**:
    ```bash
    python -m pip install -r requirements.txt
    # OR manually:
    python -m pip install fastapi uvicorn sqlalchemy aiosqlite jinja2 pydantic-settings asyncpg redis arq playwright beautifulsoup4 weasyprint openai
    ```

2.  **Seed Database**:
    ```bash
    python seed_data.py
    ```

3.  **Run Server**:
    ```bash
    python -m uvicorn app.main:app --reload
    ```

4.  **Open Demo**:
    Go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 5. Deployment Notes (Vercel vs VPS)
-   **Vercel**: Good for frontend/Next.js. **Hard** for this backend because:
    -   Playwright requires system browsers (heavy).
    -   Vercel Functions have 10s-60s timeouts (crawling takes longer).
    -   No persistent SQLite (need external Postgres).
-   **Recommended**: Docker-based hosting (Railway, Render, Fly.io, or DigitalOcean VPS).

