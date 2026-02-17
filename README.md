# AI Compliance & Onboarding Agent

## 1. Project Context
**Goal**: Internal tool for analyzing merchant website readiness for compliance audits and low-risk categorization by payment processing partners.

**Core Value**: Automated website compliance checks (Privacy Policy, Terms of Service, Refund Policy, Contact Details) with AI-powered content extraction and deterministic rule-based scoring.

## 2. Architecture: Modular Monolith
- **Core**: Shared infrastructure (DB, Config, Logging).
- **Modules**: Loose coupling between domains (`compliance`, `policies`).
- **AI Layer**: Abstracted LLM access via `LLMFactory`. Supports OpenAI, Gemini, and Mock (demo) providers.
- **Crawler**: Playwright-based with SSRF protection and HTML sanitization.

### Tech Stack
- **Runtime**: Python 3.11
- **Framework**: FastAPI (Async)
- **Database**: SQLite + aiosqlite (production-ready for single-instance use; Supabase/PostgreSQL upgrade path available)
- **ORM**: SQLAlchemy 2.0 (async)
- **Browser**: Playwright (headless Chromium)
- **Reports**: python-docx (DOCX generation)

## 3. Features

### ✅ Implemented
- **Compliance Check**: Enter a URL → crawl → AI extraction → deterministic rule scoring → DOCX report download
- **Rule Engine**: Python-based compliance logic (no LLM hallucinations for rules)
- **LLM Abstraction**: `LLMFactory` supporting OpenAI, Gemini, and Mock providers
- **SSRF Protection**: URL validation blocks internal/private IP ranges
- **Dynamic Policy Widget**: Shadow DOM JS widget with Jinja2 sandboxed rendering
- **Demo Mode**: Full workflow works without API keys (`LLM_PROVIDER=mock`)

### 🗺️ Roadmap
- Real LLM integration (OpenAI/Gemini with production keys)
- Extended compliance rules (KYC/AML-specific checks)
- API authentication for future integrations
- PostgreSQL/Supabase migration
- Rate limiting

## 4. Setup & Run

### Prerequisites
- Python 3.11+
- (Optional) Docker for deployment

### Quick Start (Local)
1. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2. **Configure** (optional — works out of the box with defaults):
    ```bash
    cp .env.example .env
    # Edit .env if you want to use real OpenAI/Gemini keys
    ```

3. **Seed Demo Data** (optional):
    ```bash
    python seed_data.py
    ```

4. **Run Server**:
    ```bash
    uvicorn app.main:app --reload
    ```

5. **Open Demo**: Go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./compliance.db` | Database connection string |
| `LLM_PROVIDER` | `mock` | AI provider: `mock`, `openai`, or `gemini` |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `GEMINI_API_KEY` | — | Required if `LLM_PROVIDER=gemini` |
| `ALLOWED_ORIGINS` | `http://localhost:8000,...` | Comma-separated CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | `development` or `production` |

## 5. Deployment (Docker)

### Railway / Render
1. Connect your GitHub repository
2. Set environment variables:
   - `LLM_PROVIDER`: `mock` (or `openai`/`gemini` with valid keys)
   - `OPENAI_API_KEY` / `GEMINI_API_KEY`: your API keys (if using real providers)
   - `ALLOWED_ORIGINS`: your deployed app URL (e.g., `https://your-app.up.railway.app`)
3. Deploy — Dockerfile handles everything automatically

> **Note**: Database tables are created automatically on first startup. No manual migration needed.

### Docker Compose (Local)
```bash
docker-compose up --build
```
