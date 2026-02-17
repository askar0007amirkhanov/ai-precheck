import ipaddress
import logging
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from app.services.crawler.sanitizer import HtmlSanitizer

logger = logging.getLogger(__name__)

# Networks that must never be crawled (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private A
    ipaddress.ip_network("172.16.0.0/12"),     # Private B
    ipaddress.ip_network("192.168.0.0/16"),    # Private C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / AWS metadata
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}


def _validate_url(url: str) -> str:
    """Validate URL for SSRF. Returns the URL or raises ValueError."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}. Only http/https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found.")

    # Block known dangerous hostnames
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname: {hostname}")

    # Try to parse as IP and check against blocked networks
    try:
        ip = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(f"Blocked internal IP address: {hostname}")
    except ValueError as e:
        if "Blocked" in str(e):
            raise
        # Not an IP — it's a domain name, that's fine
        pass

    return url


class CrawlerService:
    def __init__(self):
        self.sanitizer = HtmlSanitizer()

    async def crawl_page(self, url: str) -> str:
        """
        Crawl a URL and return cleaned text content.
        Validates URL against SSRF before proceeding.
        Falls back to mock content if Playwright is unavailable.
        """
        # SSRF protection: validate before any network call
        url = _validate_url(url)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    page = await browser.new_page()
                    page.set_default_timeout(30000)

                    logger.info("Crawling: %s", url)
                    await page.goto(url, wait_until="networkidle")
                    content = await page.content()

                    return self.sanitizer.clean_html(content)
                finally:
                    await browser.close()
        except Exception as e:
            logger.warning("Playwright failed, using mock content. Error: %s", e)
            return (
                f"Mock Content for {url}: Privacy Policy provided. "
                "Terms of Service missing. Contact: support@demo.com"
            )
