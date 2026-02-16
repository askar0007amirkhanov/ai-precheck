from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.api.widget.router import router as widget_router
from app.api.compliance.router import router as compliance_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Compliance Agent",
    version="0.1.0",
    description="Compliance & Onboarding Agent with Modular Monolith Architecture"
)

# Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(widget_router, prefix="/api/widget", tags=["Widget"])
app.include_router(compliance_router, prefix="/api/compliance", tags=["Compliance"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    from app.infrastructure.database import DB_INITIALIZED
    status = "ok" if DB_INITIALIZED else "degraded_no_db"
    return {"status": status, "version": settings.VERSION, "db_connected": DB_INITIALIZED}
