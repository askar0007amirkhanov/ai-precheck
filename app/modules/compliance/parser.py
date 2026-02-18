"""
Parser service for uploading checklist files (PDF/DOCX/TXT) and converting them
to structured DynamicChecklistRule objects using Gemini.
"""
import logging
import io
from fastapi import UploadFile, HTTPException
import pypdf
import docx

from app.services.llm.gemini_client import GeminiClient
from app.services.llm.mock_client import MockClient
from app.modules.compliance.schemas import DynamicChecklist, DynamicChecklistRule
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChecklistParser:
    def __init__(self):
        if settings.LLM_PROVIDER == "gemini":
            self.llm = GeminiClient()
        else:
            self.llm = MockClient()

    async def parse_file(self, file: UploadFile) -> DynamicChecklist:
        """Extract text from file and parse into structured rules via LLM."""
        content = await file.read()
        filename = file.filename.lower()
        text = ""

        # 1. Extract Text
        try:
            if filename.endswith(".pdf"):
                pdf = pypdf.PdfReader(io.BytesIO(content))
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            elif filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(content))
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif filename.endswith(".txt"):
                text = content.decode("utf-8")
            else:
                raise ValueError("Unsupported file type. Use PDF, DOCX, or TXT.")
        except Exception as e:
            logger.error(f"Failed to extract text from {filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

        if len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="File is empty or contains no extractable text.")

        # 2. LLM Extraction
        if isinstance(self.llm, MockClient):
            return self._mock_response()

        prompt = (
            f"You are a compliance expert. Convert this checklist document into a structured JSON format.\n"
            f"Create a list of rules based on the requirements found in the text.\n\n"
            f"For each rule, define:\n"
            f"- rule_id: A unique code (e.g. SEC-01)\n"
            f"- section: The section it belongs to (e.g. 'Company Info')\n"
            f"- item: Short name (e.g. 'Privacy Policy link')\n"
            f"- description: Full requirement details from the text\n"
            f"- extraction_prompt: A specific instruction for an AI agent to check this specific rule on a website text. "
            f"Example: 'Find the company registration number on the page'.\n"
            f"- pass_condition: 'not_empty' (if finding any value passes), 'true' (if boolean check must be true)\n"
            f"- severity: 'fail' (critical) or 'warning' (minor)\n\n"
            f"DOCUMENT CONTENT (truncated to first 30k chars):\n{text[:30000]}"
        )

        try:
            result = await self.llm.extract_data(
                text=prompt,
                schema=DynamicChecklist,
                system_prompt="Extract structured compliance rules from the document."
            )
            return result
        except Exception as e:
            logger.error(f"Gemini parsing failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse checklist rules with AI.")

    def _mock_response(self) -> DynamicChecklist:
        """Return a dummy checklist for testing without Gemini."""
        return DynamicChecklist(
            name="Mock Checklist",
            rules=[
                DynamicChecklistRule(
                    rule_id="MOCK-001",
                    section="Mock Section",
                    item="Mock Rule 1",
                    description="This is a mock rule from parser.",
                    extraction_prompt="Find mock value",
                    pass_condition="not_empty",
                    severity="fail"
                )
            ]
        )
