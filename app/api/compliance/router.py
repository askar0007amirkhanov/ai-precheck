from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from app.services.crawler.service import CrawlerService
from app.modules.compliance.engine import ComplianceRuleEngine
from app.services.report.docx_service import DocxService
from fastapi.responses import Response


router = APIRouter()

class ComplianceRequest(BaseModel):
    url: HttpUrl
    company_name: str

@router.post("/check", summary="Run full compliance check")
async def run_compliance_check(request: ComplianceRequest):
    print(f"Received request for {request.company_name}")
    try:
        crawler = CrawlerService()
        engine = ComplianceRuleEngine()
        docx_service = DocxService()

        # 1. Crawl
        try:
            print(f"Starting crawl for {request.url}") 
            clean_text = await crawler.crawl_page(str(request.url))
            print(f"Crawl successful. Text length: {len(clean_text)}")
        except Exception as e:
            print(f"Crawl ERROR: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to crawl site: {str(e)}")

        # 2. Analyze
        try:
            print("Starting analysis...")
            report = await engine.analyze_site(clean_text)
            print(f"Analysis complete. Score: {report.score}")
        except Exception as e:
            print(f"Analysis ERROR: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
        # 3. Generate DOCX
        try:
            print("Generating DOCX...")
            file_bytes = docx_service.generate_report(report.model_dump())
            print(f"DOCX generated. Bytes: {len(file_bytes)}")
        except Exception as e:
            print(f"DOCX Gen ERROR: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Report Generation failed: {str(e)}")

        from urllib.parse import quote
        filename = f"compliance_report_{quote(request.company_name)}.docx"
        
        return Response(
            content=file_bytes, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"CRITICAL API ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Critical Server Error: {type(e).__name__}: {str(e)}")
