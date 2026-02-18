import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from urllib.parse import quote

from app.services.crawler.service import CrawlerService
from app.modules.compliance.engine import ComplianceRuleEngine
from app.services.report.docx_service import DocxService
from app.modules.policies.generator import PolicyGenerator, POLICY_TYPES
from app.modules.compliance.schemas import DynamicChecklistRule
from app.modules.compliance.parser import ChecklistParser

logger = logging.getLogger(__name__)

router = APIRouter()


class ComplianceRequest(BaseModel):
    url: HttpUrl
    company_name: str
    custom_rules: Optional[List[DynamicChecklistRule]] = None
    model: Optional[str] = None  # e.g. 'gemini-2.5-flash', 'gemini-2.5-pro'


@router.post("/check", summary="Run full compliance check")
async def run_compliance_check(request: ComplianceRequest):
    logger.info("Compliance check requested for '%s' (%s)", request.company_name, request.url)

    crawler = CrawlerService()
    engine = ComplianceRuleEngine(model=request.model)
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
        report_data = report.model_dump()
        report_data["site_url"] = str(request.url)
        file_bytes = docx_service.generate_report(report_data)
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


@router.post("/check-json", summary="Run compliance check (return JSON)")
async def run_compliance_check_json(request: ComplianceRequest):
    """
    Run compliance check and return JSON results.
    Used by the web frontend to show results before downloading.
    """
    logger.info("JSON Compliance check requested for '%s' (%s)", request.company_name, request.url)

    crawler = CrawlerService()
    engine = ComplianceRuleEngine(model=request.model)

    # 1. Crawl
    try:
        clean_text = await crawler.crawl_page(str(request.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Crawl failed: %s", e)
        raise HTTPException(status_code=400, detail="Failed to crawl the website.")

    # 2. Analyze
    try:
        if request.custom_rules:
            logger.info("Using %d custom rules for analysis", len(request.custom_rules))
            report = await engine.analyze_dynamic(clean_text, request.custom_rules)
        else:
            report = await engine.analyze_site(clean_text)
    except Exception as e:
        logger.error("Analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Compliance analysis failed.")

    return report


class GeneratePolicyRequest(BaseModel):
    policy_type: str
    company_name: str
    url: HttpUrl


@router.post("/generate-policy", summary="Generate single policy (public demo)")
async def generate_policy_public(request: GeneratePolicyRequest):
    """
    Generate a single policy for the web frontend demo.
    No auth required, no DB storage.
    """
    if request.policy_type not in POLICY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid policy type. Valid: {list(POLICY_TYPES.keys())}",
        )

    generator = PolicyGenerator()
    
    # Simple heuristic for jurisdiction/language since we don't have full context here
    # could be improved by passing more data from frontend
    jurisdiction = "GENERAL" 
    language = "English"

    html_content = await generator.generate_policy(
        policy_type=request.policy_type,
        company_name=request.company_name,
        legal_address="[Address not provided]",
        support_email="[Email not provided]",
        site_url=str(request.url),
        jurisdiction=jurisdiction,
        language=language,
    )

    return {"html": html_content}


@router.post("/upload-checklist", summary="Parse uploaded checklist file")
async def upload_checklist(file: UploadFile = File(...)):
    """
    Parse an uploaded checklist file (PDF/DOCX/TXT) into structured rules
    using Gemini.
    """
    logger.info("Processing checklist upload: %s", file.filename)
    parser = ChecklistParser()
    return await parser.parse_file(file)
