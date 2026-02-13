from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.core.config import settings
import logging

# Optional WeasyPrint support (requires GTK on Windows)
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except OSError:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint not available (missing GTK libraries). PDF generation will be mocked.")

class PdfService:
    def __init__(self):
        self.template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_report(self, data: Dict[str, Any], output_path: str = None) -> bytes:
        """
        Generate a PDF compliance report from data.
        
        :param data: Dictionary containing report data (score, issues, company_name, etc.)
        :param output_path: Optional path to save the PDF file.
        :return: PDF bytes.
        """
        template = self.env.get_template("compliance_report.html")
        
        # Render HTML
        html_string = template.render(**data)
        
        if WEASYPRINT_AVAILABLE:
            # Generator PDF
            # Use simple CSS for clean layout
            doc = HTML(string=html_string)
            pdf_bytes = doc.write_pdf(target=output_path)
        else:
            # Fallback for Windows/Local Dev without GTK
            # Return HTML bytes but pretend it's PDF for the browser to download
            # Or return a simple text PDF representation if possible, but HTML is better for debug
            logging.warning("Generating HTML fallback instead of PDF")
            pdf_bytes = html_string.encode('utf-8')
        
        return pdf_bytes
