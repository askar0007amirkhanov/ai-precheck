"""
V1 Compliance API router — server-to-server with API key auth + rate limiting.
Used by portal.nbcgate.com backend.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from typing import Optional
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.auth import require_api_key
from app.api.v1.rate_limiter import check_rate_limit
from app.infrastructure.database import get_db
from app.services.crawler.service import CrawlerService
from app.modules.compliance.engine import ComplianceRuleEngine
from app.services.report.docx_service import DocxService
from app.modules.policies.models import ComplianceReportRecord

logger = logging.getLogger(__name__)

router = APIRouter()


class ComplianceCheckRequest(BaseModel):
    url: HttpUrl
    company_name: str
    client_id: str  # unique merchant ID from portal


class ComplianceCheckResponse(BaseModel):
    report_id: str
    score: int
    status: str
    summary: str
    checklist: list
    download_url: str


@router.post("/check", response_model=ComplianceCheckResponse, summary="Run compliance check (rate limited)")
async def run_compliance_check_v1(
    request: ComplianceCheckRequest,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Run a full compliance check. Rate limited: 1 per client per day.
    Requires Authorization: Bearer <API_KEY>.
    """
    # Rate limit check
    await check_rate_limit(request.client_id, db)

    crawler = CrawlerService()
    engine = ComplianceRuleEngine()

    # 1. Crawl
    try:
        logger.info("V1 check for client=%s url=%s", request.client_id, request.url)
        clean_text = await crawler.crawl_page(str(request.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Crawl failed: %s", e)
        raise HTTPException(status_code=400, detail="Failed to crawl the website.")

    # 2. Analyze
    try:
        report = await engine.analyze_site(clean_text)
    except Exception as e:
        logger.error("Analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Compliance analysis failed.")

    # 3. Save to DB
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    report_data = report.model_dump()

    record = ComplianceReportRecord(
        id=report_id,
        client_id=request.client_id,
        site_url=str(request.url),
        company_name=request.company_name,
        score=report_data["score"],
        status=report_data["status"],
        checklist=report_data.get("checklist"),
        summary=report_data.get("summary"),
    )
    db.add(record)
    await db.commit()

    logger.info("V1 check complete: report_id=%s score=%d", report_id, report.score)

    return ComplianceCheckResponse(
        report_id=report_id,
        score=report_data["score"],
        status=report_data["status"],
        summary=report_data.get("summary", ""),
        checklist=report_data.get("checklist", []),
        download_url=f"/api/v1/compliance/reports/{report_id}/download",
    )


@router.get("/reports/{report_id}", summary="Get report JSON")
async def get_report(
    report_id: str,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a saved compliance report by ID."""
    stmt = select(ComplianceReportRecord).where(ComplianceReportRecord.id == report_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {
        "report_id": record.id,
        "client_id": record.client_id,
        "site_url": record.site_url,
        "company_name": record.company_name,
        "score": record.score,
        "status": record.status,
        "checklist": record.checklist,
        "summary": record.summary,
        "created_at": str(record.created_at) if record.created_at else None,
    }


@router.get("/reports/{report_id}/download", summary="Download DOCX report")
async def download_report(
    report_id: str,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Download a compliance report as DOCX."""
    stmt = select(ComplianceReportRecord).where(ComplianceReportRecord.id == report_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")

    docx_service = DocxService()
    report_data = {
        "company_name": record.company_name,
        "site_url": record.site_url,
        "score": record.score,
        "status": record.status,
        "summary": record.summary,
        "checklist": record.checklist or [],
    }
    file_bytes = docx_service.generate_report(report_data)
    filename = f"compliance_report_{quote(record.company_name)}.docx"

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
