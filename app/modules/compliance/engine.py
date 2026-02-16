from datetime import datetime
from typing import List
from app.modules.compliance.schemas import ComplianceReport, RuleCheckResult, SiteContentExtraction
from app.services.llm.factory import LLMFactory

from app.core.config import settings

class ComplianceRuleEngine:
    def __init__(self, llm_provider: str = None):
        self.provider = llm_provider or settings.LLM_PROVIDER
        self.llm_client = LLMFactory.get_client(self.provider)

    async def analyze_site(self, clean_text: str) -> ComplianceReport:
        # 1. Extract Data via LLM (Non-deterministic part, constrained by schema)
        extracted_data: SiteContentExtraction = await self.llm_client.extract_data(
            text=clean_text[:50000], # Limit context
            schema=SiteContentExtraction,
            system_prompt="Extract regulatory compliance details from the website text."
        )

        # 2. Apply Deterministic Rules (Python logic)
        issues: List[RuleCheckResult] = []
        score = 100
        recs = []

        # Rule 1: Existence of Policies
        if not extracted_data.has_privacy_policy:
            score -= 20
            issues.append(RuleCheckResult(
                rule_id="POL-001", status="fail", 
                description="Missing Privacy Policy",
                recommendation="Add a clearly visible Privacy Policy link in the footer."
            ))
        
        if not extracted_data.has_terms_of_service:
            score -= 20
            issues.append(RuleCheckResult(
                rule_id="POL-002", status="fail", 
                description="Missing Terms of Service",
                recommendation="Add Terms of Service."
            ))

        # Rule 2: Refund Policy
        if not extracted_data.has_refund_policy:
            score -= 15
            issues.append(RuleCheckResult(
                rule_id="POL-003", status="warning", 
                description="Missing Refund Policy",
                recommendation="It is recommended to have a clear Refund Policy."
            ))
        elif extracted_data.refund_period_days is not None and extracted_data.refund_period_days < 14:
            # Example logic: EU requires 14 days usually
            issues.append(RuleCheckResult(
                rule_id="POL-003-TIME", status="warning",
                description=f"Refund period ({extracted_data.refund_period_days} days) may be too short.",
                recommendation="Consider extending refund period to at least 14 days for EU compliance."
            ))

        # Rule 3: Contact Details
        if not extracted_data.has_contact_details:
            score -= 10
            issues.append(RuleCheckResult(
                rule_id="CTC-001", status="fail",
                description="No Contact Details found",
                recommendation="Add a physical address, email, or phone number."
            ))

        # Compile Recommendations
        for issue in issues:
            if issue.recommendation:
                recs.append(issue.recommendation)
        
        if score < 0: score = 0

        return ComplianceReport(
            company_name=extracted_data.company_name or "Unknown",
            score=score,
            critical_issues=[i for i in issues if i.status == "fail"],
            recommendations=recs,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )
