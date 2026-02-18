"""
Policy generation engine — uses Gemini to generate compliance policies.
"""
import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.llm.gemini_client import GeminiClient
from app.services.llm.mock_client import MockClient
from app.modules.policies.models import ClientPolicy
from app.core.config import settings

logger = logging.getLogger(__name__)

POLICY_TYPES = {
    "terms": "Terms & Conditions",
    "privacy": "Privacy Policy",
    "refund": "Refund / Return Policy",
    "cancellation": "Cancellation Policy",
    "payment": "Payment Policy",
}

# Jurisdiction-specific clauses to include
JURISDICTION_CLAUSES = {
    "EU": {
        "privacy": "Include GDPR rights (access, erasure, portability, objection), legal basis for processing, DPO contact, data retention periods, right to lodge complaint with supervisory authority.",
        "refund": "Include 14-day cooling-off period per EU Consumer Rights Directive.",
        "terms": "Include governing law (EU member state), dispute resolution per ODR regulation.",
    },
    "UK": {
        "privacy": "Include UK GDPR rights, ICO as supervisory authority, lawful basis for processing.",
        "refund": "Include 14-day cancellation right per Consumer Contracts Regulations 2013, Consumer Rights Act 2015.",
        "terms": "Include governing law (England and Wales / Scotland), Consumer Rights Act 2015 references.",
    },
    "CY": {
        "privacy": "Include GDPR rights, Commissioner for Personal Data Protection as supervisory authority.",
        "refund": "Include EU Distance Selling Directive cooling-off period.",
        "terms": "Include Cyprus company registration (HE number), governing law of Republic of Cyprus.",
    },
    "US": {
        "privacy": "Include CCPA/CPRA rights for California residents (right to know, delete, opt-out of sale), state-specific disclosures.",
        "refund": "No federal return law; state disclosure if return policy exists; FTC requirements for guarantees.",
        "terms": "Include governing law (state), arbitration clause if applicable, DMCA safe harbor.",
    },
    "GENERAL": {
        "privacy": "Include data collection purposes, third-party sharing, user rights, cookie usage.",
        "refund": "Include refund conditions, time limits, process for requesting refund.",
        "terms": "Include service description, user obligations, limitation of liability, governing law.",
    },
}

DISCLAIMER = (
    "<div style='background:#fff3cd;border:1px solid #ffc107;padding:12px;margin-bottom:16px;"
    "border-radius:4px;font-size:13px;color:#856404;'>"
    "<strong>⚠️ Disclaimer:</strong> This policy was auto-generated based on standard compliance "
    "requirements and does not constitute legal advice. We strongly recommend having this document "
    "reviewed by a qualified legal professional before publishing."
    "</div>"
)


class PolicyGenerator:
    """Generate compliance policies using Gemini."""

    def __init__(self):
        if settings.LLM_PROVIDER == "gemini":
            self.llm = GeminiClient()
        else:
            self.llm = MockClient()

    async def generate_policy(
        self,
        policy_type: str,
        company_name: str,
        legal_address: str,
        support_email: str,
        site_url: str,
        jurisdiction: str = "GENERAL",
        language: str = "English",
    ) -> str:
        """Generate a single policy using Gemini."""
        policy_name = POLICY_TYPES.get(policy_type, policy_type)

        # Get jurisdiction-specific clauses
        jur_clauses = JURISDICTION_CLAUSES.get(jurisdiction, JURISDICTION_CLAUSES["GENERAL"])
        extra_clauses = jur_clauses.get(policy_type, "")

        prompt = (
            f"Generate a professional {policy_name} for a company with the following details:\n\n"
            f"Company Name: {company_name}\n"
            f"Legal Address: {legal_address}\n"
            f"Support Email: {support_email}\n"
            f"Website: {site_url}\n"
            f"Jurisdiction: {jurisdiction}\n\n"
        )

        if extra_clauses:
            prompt += f"IMPORTANT — Include these jurisdiction-specific clauses:\n{extra_clauses}\n\n"

        prompt += (
            f"Requirements:\n"
            f"- Write in {language}\n"
            f"- Format as HTML (use <h2>, <h3>, <p>, <ul>, <li> tags)\n"
            f"- Be comprehensive but clear\n"
            f"- Include a 'Last Updated' date of today\n"
            f"- Use formal legal language appropriate for a commercial website\n"
            f"- Replace placeholder values with the actual company details provided\n"
            f"- Include all standard sections expected for this type of policy\n"
            f"- Do NOT include any <html>, <head>, or <body> tags — just the content\n"
        )

        if settings.LLM_PROVIDER == "mock":
            # Return a mock policy for testing
            return self._mock_policy(policy_type, company_name, language)

        from pydantic import BaseModel

        class PolicyContent(BaseModel):
            html: str

        result = await self.llm.extract_data(
            text=prompt,
            schema=PolicyContent,
            system_prompt="You are a legal document generator. Generate the requested policy document as clean HTML.",
        )
        return DISCLAIMER + result.html

    def _mock_policy(self, policy_type: str, company_name: str, language: str) -> str:
        """Return a mock policy for testing without API."""
        policy_name = POLICY_TYPES.get(policy_type, policy_type)
        return (
            f"{DISCLAIMER}"
            f"<h2>{policy_name}</h2>"
            f"<p><strong>Company:</strong> {company_name}</p>"
            f"<p>This is a demo {policy_name.lower()} generated for testing purposes. "
            f"Language: {language}.</p>"
            f"<p>In production, this would be a comprehensive legal document generated "
            f"by Gemini AI with jurisdiction-specific clauses.</p>"
            f"<p><em>Last Updated: 2026-02-17</em></p>"
        )

    async def generate_missing_policies(
        self,
        missing_types: List[str],
        company_name: str,
        legal_address: str,
        support_email: str,
        site_url: str,
        jurisdiction: str = "GENERAL",
        language: str = "English",
        client_id: str = "",
        db: Optional[AsyncSession] = None,
    ) -> List[dict]:
        """Generate multiple missing policies and optionally save to DB."""
        results = []

        for policy_type in missing_types:
            if policy_type not in POLICY_TYPES:
                logger.warning("Unknown policy type: %s", policy_type)
                continue

            logger.info("Generating %s for %s (jurisdiction=%s)", policy_type, company_name, jurisdiction)
            content_html = await self.generate_policy(
                policy_type=policy_type,
                company_name=company_name,
                legal_address=legal_address,
                support_email=support_email,
                site_url=site_url,
                jurisdiction=jurisdiction,
                language=language,
            )

            policy_id = f"pol_{uuid.uuid4().hex[:12]}"
            policy_data = {
                "id": policy_id,
                "client_id": client_id,
                "policy_type": policy_type,
                "content_html": content_html,
                "jurisdiction": jurisdiction,
                "language": language,
                "status": "draft",
                "version": 1,
            }

            # Save to DB if session provided
            if db:
                record = ClientPolicy(**policy_data)
                db.add(record)
                results.append(policy_data)
            else:
                results.append(policy_data)

        if db:
            await db.commit()

        logger.info("Generated %d policies for client %s", len(results), client_id)
        return results
