import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock weasyprint before importing app modules that depend on it
sys.modules["weasyprint"] = MagicMock()

import pytest
from app.modules.compliance.engine import ComplianceRuleEngine
from app.modules.compliance.schemas import SiteContentExtraction
from app.services.crawler.service import CrawlerService
from app.services.pdf.service import PdfService

@pytest.mark.asyncio
async def test_compliance_workflow():
    # 1. Mock Crawler
    with patch("app.services.crawler.service.async_playwright") as mock_playwright:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        # Mock the context manager for playwright
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body><footer>Privacy Policy</footer></body></html>"
        
        crawler = CrawlerService()
        # Mock sanitizer to return clean text
        crawler.sanitizer.clean_html = MagicMock(return_value="Privacy Policy Contact: info@example.com")
        
        text = await crawler.crawl_page("http://example.com")
        assert text == "Privacy Policy Contact: info@example.com"

    # 2. Mock LLM Extraction
    with patch("app.services.llm.factory.LLMFactory.get_client") as mock_factory:
        mock_client = AsyncMock()
        mock_factory.return_value = mock_client # The factory returns the client instance directly in our impl, wait, let's check factory.py
        # Factory.get_client returns an instance.
        
        # Define mock extracted data
        mock_data = SiteContentExtraction(
            company_name="Example Corp",
            has_privacy_policy=True,
            has_terms_of_service=False, # Should trigger issue
            has_refund_policy=True,
            refund_period_days=30,
            has_contact_details=True,
            payment_methods_mentioned=["Visa"]
        )
        mock_client.extract_data.return_value = mock_data

        engine = ComplianceRuleEngine()
        # We need to make sure the engine uses our mocked client. 
        # Since engine init calls factory, and we patched factory...
        
        report = await engine.analyze_site(text)
        
        assert report.company_name == "Example Corp"
        assert report.score < 100 # Should lose points for missing ToS
        assert any(i.rule_id == "POL-002" for i in report.critical_issues)

    # 3. Test PDF Generation
    # Configure the global mock to return bytes
    # HTML() returns a document mock, .write_pdf() returns the bytes
    sys.modules["weasyprint"].HTML.return_value.write_pdf.return_value = b"%PDF-1.4 mock pdf content..."
    
    pdf_service = PdfService()
    pdf_bytes = pdf_service.generate_report(report.model_dump())
    assert len(pdf_bytes) > 0
    assert b"%PDF" in pdf_bytes[:10]
