from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class RuleCheckResult(BaseModel):
    rule_id: str
    status: Literal["pass", "fail", "warning"]
    description: str
    recommendation: Optional[str] = None

class ComplianceReport(BaseModel):
    company_name: str = "Unknown"
    score: int
    critical_issues: List[RuleCheckResult]
    recommendations: List[str]
    generated_at: str

# Schema for LLM Extraction
class SiteContentExtraction(BaseModel):
    company_name: Optional[str] = Field(description="Name of the company found in the footer or contact page")
    has_privacy_policy: bool = Field(description="Is there a link to a privacy policy?")
    has_terms_of_service: bool = Field(description="Is there a link to terms of service?")
    has_refund_policy: bool = Field(description="Is there a link to a refund policy?")
    has_contact_details: bool = Field(description="Are there contact details (email, phone, address)?")
    payment_methods_mentioned: List[str] = Field(description="List of payment methods mentioned (e.g. Visa, Crypto, PayPal)")
    
    # Specific policy details for rule checking
    refund_period_days: Optional[int] = Field(description="Number of days mentioned for refunds. Return 0 if not mentioned or no refunds.")
    privacy_policy_mentions_gdpr: bool = False
