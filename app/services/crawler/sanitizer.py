import re
from bs4 import BeautifulSoup

class HtmlSanitizer:
    @staticmethod
    def clean_html(html_content: str) -> str:
        """
        Convert raw HTML to clean, readable text.
        Removes scripts, styles, and unsafe content.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "noscript", "iframe", "svg"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # Truncate if too long (simple safety guard, though LLM client should also handle)
        return text[:100000] # Cap at ~100k chars to avoid DoS
