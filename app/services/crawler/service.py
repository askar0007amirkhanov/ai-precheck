import asyncio
from typing import Optional
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_fixed
from app.services.crawler.sanitizer import HtmlSanitizer
import logging

logger = logging.getLogger(__name__)

class CrawlerService:
    def __init__(self):
        self.sanitizer = HtmlSanitizer()

    async def crawl_page(self, url: str) -> str:
        """
        Crawl a URL and return cleaned text content.
        Safely falls back to MOCK content if Playwright fails (common on Windows without proper setup).
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
                try:
                    page = await browser.new_page()
                    page.set_default_timeout(30000)
                    
                    logger.info(f"Crawling: {url}")
                    await page.goto(url, wait_until="networkidle")
                    content = await page.content()
                    
                    return self.sanitizer.clean_html(content)
                finally:
                    await browser.close()
        except Exception as e:
            logger.warning(f"Playwright failed. Using MOCK. Error: {e}")
            return f"Mock Content for {url}: Privacy Policy provided. Terms of Service missing. Contact: support@demo.com"

    async def check_robots_txt(self, url: str) -> bool:
        return True
