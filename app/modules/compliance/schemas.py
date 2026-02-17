from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# --- LLM Extraction Schema (what Gemini extracts from the site) ---

class SiteContentExtraction(BaseModel):
    """Schema for LLM to extract all compliance-relevant data from website text."""

    # Section 1: Company Information
    company_name: Optional[str] = Field(
        None, description="Full legal company name found on the website"
    )
    registration_number: Optional[str] = Field(
        None, description="Company registration / incorporation number"
    )
    legal_address: Optional[str] = Field(
        None, description="Legal / registered address of the company"
    )
    vat_number: Optional[str] = Field(
        None, description="VAT or tax identification number"
    )
    merchant_outlet_location: Optional[str] = Field(
        None, description="Physical location where business decisions are made"
    )
    has_license_info: bool = Field(
        False, description="Is there any licensing information (regulator, license number)?"
    )
    license_number: Optional[str] = Field(
        None, description="License number if found"
    )
    regulator_link: Optional[str] = Field(
        None, description="Link or mention of the regulatory authority"
    )

    # Section 2: Contacts
    support_email: Optional[str] = Field(
        None, description="Support or contact email address"
    )
    phone_number: Optional[str] = Field(
        None, description="Contact phone number"
    )
    physical_address: Optional[str] = Field(
        None, description="Physical / mailing address (may differ from legal address)"
    )
    has_contact_page: bool = Field(
        False, description="Is there a dedicated Contact Us page or section?"
    )

    # Section 3: Policies
    has_terms_conditions: bool = Field(
        False, description="Is there a link or page for Terms & Conditions?"
    )
    has_privacy_policy: bool = Field(
        False, description="Is there a link or page for Privacy Policy?"
    )
    has_refund_policy: bool = Field(
        False, description="Is there a link or page for Refund / Return Policy?"
    )
    has_cancellation_policy: bool = Field(
        False, description="Is there a link or page for Cancellation Policy?"
    )
    has_payment_policy: bool = Field(
        False, description="Is there a link or page for Payment Policy?"
    )
    policies_accessible_from_all_pages: bool = Field(
        False, description="Are policy links present in footer or menu, accessible from every page?"
    )
    policy_mentions_service_conditions: bool = Field(
        False, description="Do policies describe conditions for providing services or selling goods?"
    )
    policy_mentions_cancellation_terms: bool = Field(
        False, description="Do policies describe cancellation conditions?"
    )
    policy_mentions_refund_terms: bool = Field(
        False, description="Do policies describe refund terms, deadlines, and rules?"
    )
    refund_period_days: Optional[int] = Field(
        None, description="Number of days for refund if mentioned"
    )
    policy_mentions_user_restrictions: bool = Field(
        False, description="Do policies mention any user restrictions (age, geography, etc.)?"
    )
    policy_mentions_company_name: bool = Field(
        False, description="Do policies explicitly mention the company name as the contracting party?"
    )
    site_primary_language: Optional[str] = Field(
        None, description="Primary language of the website content"
    )

    # Section 4: Product/Service Description
    has_product_description: bool = Field(
        False, description="Are products or services described in detail?"
    )
    prices_in_purchase_currency: bool = Field(
        False, description="Are prices shown in the purchase/local currency?"
    )
    all_fees_disclosed: bool = Field(
        False, description="Are all fees, commissions, and additional charges clearly disclosed?"
    )
    transparent_purchase_process: bool = Field(
        False, description="Is the purchase process clear and transparent to the buyer?"
    )

    # Section 5: Checkout
    shows_final_price: bool = Field(
        False, description="Is the final total price shown before payment?"
    )
    shows_merchant_location_at_checkout: bool = Field(
        False, description="Is the Merchant Outlet Location shown at the final checkout step?"
    )
    has_terms_agreement_checkbox: bool = Field(
        False, description="Is there a checkbox for agreeing to Terms & Conditions / Refund Policy before purchase?"
    )

    # Section 6: Receipt Information (may not be verifiable from crawl)
    has_receipt_info: bool = Field(
        False, description="Is there any evidence of electronic receipt generation (order confirmation page, email receipt mention)?"
    )

    # Section 8: Mobile Compliance
    has_mobile_responsive: bool = Field(
        False, description="Does the site appear to have responsive/mobile-friendly design (viewport meta tag, responsive CSS)?"
    )

    # Extra: Payment methods
    payment_methods_mentioned: List[str] = Field(
        default_factory=list, description="List of payment methods mentioned (e.g. Visa, Mastercard, PayPal)"
    )


# --- Checklist Item (output per-check result) ---

class ChecklistItem(BaseModel):
    section: str = Field(description="Section name, e.g. '1. Company Information'")
    item: str = Field(description="Check item name, e.g. 'Legal company name'")
    rule_id: str = Field(description="Rule identifier, e.g. 'CMP-001'")
    status: Literal["pass", "fail", "warning", "info"] = Field(
        description="Check result"
    )
    found_value: Optional[str] = Field(
        None, description="What was found on the site, or 'Not found'"
    )
    recommendation: Optional[str] = Field(
        None, description="Recommendation if check failed"
    )


# --- Final Compliance Report ---

class ComplianceReport(BaseModel):
    company_name: str = "Unknown"
    score: int = Field(description="Overall compliance score 0-100")
    status: Literal["COMPLIANT", "NON-COMPLIANT", "NEEDS_REVIEW"] = Field(
        description="Overall compliance status"
    )
    checklist: List[ChecklistItem] = Field(
        default_factory=list, description="All checklist items with results"
    )
    summary: str = Field(
        default="", description="Brief text summary of findings"
    )
    generated_at: str = ""
