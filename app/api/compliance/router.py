import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from urllib.parse import quote

from app.services.crawler.service import CrawlerService
from app.modules.compliance.engine import ComplianceRuleEngine
from app.services.report.docx_service import DocxService

logger = logging.getLogger(__name__)

router = APIRouter()


class ComplianceRequest(BaseModel):
    url: HttpUrl
    company_name: str


@router.post("/check", summary="Run full compliance check")
async def run_compliance_check(request: ComplianceRequest):
    logger.info("Compliance check requested for '%s' (%s)", request.company_name, request.url)

    crawler = CrawlerService()
    engine = ComplianceRuleEngine()
    docx_service = DocxService()

    # 1. Crawl
    try:
        logger.info("Starting crawl for %s", request.url)
        clean_text = await crawler.crawl_page(str(request.url))
        logger.info("Crawl successful. Text length: %d", len(clean_text))
    except ValueError as e:
        # SSRF validation or bad URL
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Crawl failed: %s", e)
        raise HTTPException(status_code=400, detail="Failed to crawl the website. Please check the URL.")

    # 2. Analyze
    try:
        logger.info("Starting compliance analysis...")
        report = await engine.analyze_site(clean_text)
        logger.info("Analysis complete. Score: %d", report.score)
    except Exception as e:
        logger.error("Analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Compliance analysis failed. Please try again.")

    # 3. Generate DOCX
    try:
        file_bytes = docx_service.generate_report(report.model_dump())
        logger.info("DOCX report generated. Size: %d bytes", len(file_bytes))
    except Exception as e:
        logger.error("DOCX generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Report generation failed. Please try again.")

    filename = f"compliance_report_{quote(request.company_name)}.docx"

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
