import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.widget.router import router as widget_router
from app.api.compliance.router import router as compliance_router
from app.api.v1.compliance_router import router as v1_compliance_router
from app.api.v1.policies_router import router as v1_policies_router
from app.api.v1.widget_router import router as v1_widget_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events for the application."""
    from app.infrastructure.database import engine, DB_INITIALIZED
    if DB_INITIALIZED and engine:
        try:
            from app.modules.policies.models import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables ensured.")
        except Exception as e:
            logger.error("Database connection failed: %s — running in degraded mode.", e)
    else:
        logger.warning("Database not initialized — running in degraded mode.")
    yield


app = FastAPI(
    title="AI Compliance Agent",
    version=settings.VERSION,
    description="Compliance & Onboarding Agent — Merchant Site Readiness Check",
    lifespan=lifespan,
)

# CORS: configured via ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- Existing routes (web form, no auth) ---
app.include_router(widget_router, prefix="/api/widget", tags=["Widget (Legacy)"])
app.include_router(compliance_router, prefix="/api/compliance", tags=["Compliance (Web Form)"])

# --- V1 API routes (API key auth, rate limiting) ---
app.include_router(v1_compliance_router, prefix="/api/v1/compliance", tags=["V1 Compliance"])
app.include_router(v1_policies_router, prefix="/api/v1/policies", tags=["V1 Policies"])
app.include_router(v1_widget_router, prefix="/api/widget", tags=["V1 Widget"])


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    from app.infrastructure.database import DB_INITIALIZED
    status = "ok" if DB_INITIALIZED else "degraded_no_db"
    return {
        "status": status,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "db_connected": DB_INITIALIZED,
    }
