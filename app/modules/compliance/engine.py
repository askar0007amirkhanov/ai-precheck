from datetime import datetime, timezone
from typing import List
from app.modules.compliance.schemas import (
    ComplianceReport, ChecklistItem, SiteContentExtraction,
)
from app.services.llm.factory import LLMFactory
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Section weights for scoring (total = 100)
SECTION_WEIGHTS = {
    "1": 15,   # Company Information
    "2": 10,   # Contacts
    "3": 25,   # Policies
    "4": 15,   # Product/Service Description
    "5": 15,   # Checkout
    "6": 10,   # Receipt
    "7": 5,    # Update Requirements (informational)
    "8": 5,    # Mobile Compliance
}


class ComplianceRuleEngine:
    def __init__(self, llm_provider: str = None):
        self.provider = llm_provider or settings.LLM_PROVIDER
        self.llm_client = LLMFactory.get_client(self.provider)

    async def analyze_site(self, clean_text: str) -> ComplianceReport:
        """
        Analyze cleaned website text against the full ECOMMBX compliance checklist.
        Uses LLM for data extraction, then applies deterministic rules.
        """
        # 1. Extract data via LLM
        extracted: SiteContentExtraction = await self.llm_client.extract_data(
            text=clean_text[:50000],
            schema=SiteContentExtraction,
            system_prompt=(
                "You are a compliance analyst. Extract all regulatory and policy "
                "information from this merchant website text. Be thorough — look for "
                "company details, contact info, all policy pages (Terms, Privacy, "
                "Refund, Cancellation, Payment), product descriptions, checkout flow "
                "details, and receipt/confirmation information. "
                "If a field is not found, return null or false."
            ),
        )

        # 2. Apply deterministic rules per section
        checklist: List[ChecklistItem] = []
        section_results = {}  # section_id -> (passed, total)

        # --- SECTION 1: Company Information ---
        s1_checks = self._check_section_1(extracted)
        checklist.extend(s1_checks)
        section_results["1"] = self._count_results(s1_checks)

        # --- SECTION 2: Contacts ---
        s2_checks = self._check_section_2(extracted)
        checklist.extend(s2_checks)
        section_results["2"] = self._count_results(s2_checks)

        # --- SECTION 3: Policies ---
        s3_checks = self._check_section_3(extracted)
        checklist.extend(s3_checks)
        section_results["3"] = self._count_results(s3_checks)

        # --- SECTION 4: Product/Service Description ---
        s4_checks = self._check_section_4(extracted)
        checklist.extend(s4_checks)
        section_results["4"] = self._count_results(s4_checks)

        # --- SECTION 5: Checkout ---
        s5_checks = self._check_section_5(extracted)
        checklist.extend(s5_checks)
        section_results["5"] = self._count_results(s5_checks)

        # --- SECTION 6: Receipt ---
        s6_checks = self._check_section_6(extracted)
        checklist.extend(s6_checks)
        section_results["6"] = self._count_results(s6_checks)

        # --- SECTION 7: Update Requirements (informational) ---
        s7_checks = self._check_section_7()
        checklist.extend(s7_checks)
        section_results["7"] = (1, 1)  # informational, always passes

        # --- SECTION 8: Mobile Compliance ---
        s8_checks = self._check_section_8(extracted)
        checklist.extend(s8_checks)
        section_results["8"] = self._count_results(s8_checks)

        # 3. Calculate weighted score
        score = self._calculate_score(section_results)

        # 4. Determine status
        fails = sum(1 for c in checklist if c.status == "fail")
        warnings = sum(1 for c in checklist if c.status == "warning")

        if score >= 80 and fails == 0:
            status = "COMPLIANT"
        elif score >= 50:
            status = "NEEDS_REVIEW"
        else:
            status = "NON-COMPLIANT"

        # 5. Build summary
        total = len([c for c in checklist if c.status != "info"])
        passed = sum(1 for c in checklist if c.status == "pass")
        summary = (
            f"Checked {total} items: {passed} passed, {fails} failed, "
            f"{warnings} warnings. Score: {score}/100. Status: {status}."
        )

        return ComplianceReport(
            company_name=extracted.company_name or "Unknown",
            score=score,
            status=status,
            checklist=checklist,
            summary=summary,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

    # ---------------------------------------------------------------
    # Section check methods
    # ---------------------------------------------------------------

    def _check_section_1(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "1. Company Information"
        items = []

        items.append(ChecklistItem(
            section=sec, item="Legal company name", rule_id="CMP-001",
            status="pass" if d.company_name else "fail",
            found_value=d.company_name or "Not found",
            recommendation=None if d.company_name else "Add full legal company name to the website.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Registration number", rule_id="CMP-002",
            status="pass" if d.registration_number else "fail",
            found_value=d.registration_number or "Not found",
            recommendation=None if d.registration_number else "Add company registration number.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Legal address", rule_id="CMP-003",
            status="pass" if d.legal_address else "fail",
            found_value=d.legal_address or "Not found",
            recommendation=None if d.legal_address else "Add the registered legal address.",
        ))
        items.append(ChecklistItem(
            section=sec, item="VAT number", rule_id="CMP-004",
            status="pass" if d.vat_number else "warning",
            found_value=d.vat_number or "Not found",
            recommendation=None if d.vat_number else "Add VAT number if applicable.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Merchant Outlet Location", rule_id="CMP-005",
            status="pass" if d.merchant_outlet_location else "fail",
            found_value=d.merchant_outlet_location or "Not found",
            recommendation=None if d.merchant_outlet_location else "Add Merchant Outlet Location (physical place of business decisions).",
        ))
        items.append(ChecklistItem(
            section=sec, item="License information", rule_id="CMP-006",
            status="pass" if d.has_license_info else "warning",
            found_value=f"License: {d.license_number or 'N/A'}, Regulator: {d.regulator_link or 'N/A'}" if d.has_license_info else "Not found",
            recommendation=None if d.has_license_info else "Add licensing info if the business requires a license.",
        ))

        return items

    def _check_section_2(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "2. Contacts"
        items = []

        items.append(ChecklistItem(
            section=sec, item="Support email", rule_id="CTC-001",
            status="pass" if d.support_email else "fail",
            found_value=d.support_email or "Not found",
            recommendation=None if d.support_email else "Add a support email address.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Phone number", rule_id="CTC-002",
            status="pass" if d.phone_number else "warning",
            found_value=d.phone_number or "Not found",
            recommendation=None if d.phone_number else "Consider adding a contact phone number.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Physical / mailing address", rule_id="CTC-003",
            status="pass" if d.physical_address else "fail",
            found_value=d.physical_address or "Not found",
            recommendation=None if d.physical_address else "Add a physical or mailing address.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Contact Us page", rule_id="CTC-004",
            status="pass" if d.has_contact_page else "fail",
            found_value="Found" if d.has_contact_page else "Not found",
            recommendation=None if d.has_contact_page else "Add a dedicated Contact Us page.",
        ))

        return items

    def _check_section_3(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "3. Policies"
        items = []

        # Policy existence
        for field, label, rule_id in [
            ("has_terms_conditions", "Terms & Conditions", "POL-001"),
            ("has_privacy_policy", "Privacy Policy", "POL-002"),
            ("has_refund_policy", "Refund / Return Policy", "POL-003"),
            ("has_cancellation_policy", "Cancellation Policy", "POL-004"),
            ("has_payment_policy", "Payment Policy", "POL-005"),
        ]:
            val = getattr(d, field)
            items.append(ChecklistItem(
                section=sec, item=label, rule_id=rule_id,
                status="pass" if val else "fail",
                found_value="Found" if val else "Not found",
                recommendation=None if val else f"Add a {label} page accessible from every page.",
            ))

        # Policy accessibility
        items.append(ChecklistItem(
            section=sec, item="Policies accessible from all pages (footer/menu)", rule_id="POL-006",
            status="pass" if d.policies_accessible_from_all_pages else "warning",
            found_value="Yes" if d.policies_accessible_from_all_pages else "Not confirmed",
            recommendation=None if d.policies_accessible_from_all_pages else "Ensure all policy links are in the footer or main menu.",
        ))

        # Policy content checks
        for field, label, rule_id in [
            ("policy_mentions_service_conditions", "Policies describe service/sale conditions", "POL-007"),
            ("policy_mentions_cancellation_terms", "Policies describe cancellation terms", "POL-008"),
            ("policy_mentions_refund_terms", "Policies describe refund terms & deadlines", "POL-009"),
            ("policy_mentions_user_restrictions", "Policies mention user restrictions", "POL-010"),
            ("policy_mentions_company_name", "Policies mention company name as contracting party", "POL-011"),
        ]:
            val = getattr(d, field)
            items.append(ChecklistItem(
                section=sec, item=label, rule_id=rule_id,
                status="pass" if val else "warning",
                found_value="Yes" if val else "Not found",
                recommendation=None if val else f"Ensure policies include: {label.lower()}.",
            ))

        # Refund period
        if d.has_refund_policy and d.refund_period_days is not None:
            ok = d.refund_period_days >= 14
            items.append(ChecklistItem(
                section=sec, item="Refund period >= 14 days", rule_id="POL-012",
                status="pass" if ok else "warning",
                found_value=f"{d.refund_period_days} days",
                recommendation=None if ok else "Consider extending refund period to at least 14 days.",
            ))

        # Site language
        items.append(ChecklistItem(
            section=sec, item="Primary language identified", rule_id="POL-013",
            status="pass" if d.site_primary_language else "info",
            found_value=d.site_primary_language or "Not determined",
            recommendation=None,
        ))

        return items

    def _check_section_4(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "4. Product/Service Description"
        items = []

        items.append(ChecklistItem(
            section=sec, item="Detailed product/service descriptions", rule_id="PRD-001",
            status="pass" if d.has_product_description else "fail",
            found_value="Found" if d.has_product_description else "Not found",
            recommendation=None if d.has_product_description else "Add detailed descriptions of goods/services.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Prices in purchase currency", rule_id="PRD-002",
            status="pass" if d.prices_in_purchase_currency else "fail",
            found_value="Yes" if d.prices_in_purchase_currency else "Not found",
            recommendation=None if d.prices_in_purchase_currency else "Show prices in the buyer's purchase currency.",
        ))
        items.append(ChecklistItem(
            section=sec, item="All fees and commissions disclosed", rule_id="PRD-003",
            status="pass" if d.all_fees_disclosed else "warning",
            found_value="Yes" if d.all_fees_disclosed else "Not confirmed",
            recommendation=None if d.all_fees_disclosed else "Disclose all additional fees and commissions.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Transparent purchase process", rule_id="PRD-004",
            status="pass" if d.transparent_purchase_process else "warning",
            found_value="Yes" if d.transparent_purchase_process else "Not confirmed",
            recommendation=None if d.transparent_purchase_process else "Make the purchase process clear and easy to follow.",
        ))

        # Payment methods
        methods = ", ".join(d.payment_methods_mentioned) if d.payment_methods_mentioned else "None found"
        items.append(ChecklistItem(
            section=sec, item="Payment methods listed", rule_id="PRD-005",
            status="pass" if d.payment_methods_mentioned else "warning",
            found_value=methods,
            recommendation=None if d.payment_methods_mentioned else "List accepted payment methods on the site.",
        ))

        return items

    def _check_section_5(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "5. Checkout Process"
        items = []

        items.append(ChecklistItem(
            section=sec, item="Final price shown before payment", rule_id="CHK-001",
            status="pass" if d.shows_final_price else "fail",
            found_value="Yes" if d.shows_final_price else "Not confirmed",
            recommendation=None if d.shows_final_price else "Show the total final price on the last step before payment.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Merchant location shown at checkout", rule_id="CHK-002",
            status="pass" if d.shows_merchant_location_at_checkout else "warning",
            found_value="Yes" if d.shows_merchant_location_at_checkout else "Not confirmed",
            recommendation=None if d.shows_merchant_location_at_checkout else "Display Merchant Outlet Location at the final checkout step.",
        ))
        items.append(ChecklistItem(
            section=sec, item="Terms agreement checkbox", rule_id="CHK-003",
            status="pass" if d.has_terms_agreement_checkbox else "fail",
            found_value="Yes" if d.has_terms_agreement_checkbox else "Not found",
            recommendation=None if d.has_terms_agreement_checkbox else "Add a checkbox: 'I agree to Terms & Conditions, Refund Policy...'",
        ))

        return items

    def _check_section_6(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "6. Receipt / Confirmation"
        items = []

        if d.has_receipt_info:
            items.append(ChecklistItem(
                section=sec, item="Electronic receipt / order confirmation", rule_id="RCP-001",
                status="pass",
                found_value="Evidence of receipt/confirmation system found",
                recommendation=None,
            ))
        else:
            items.append(ChecklistItem(
                section=sec, item="Electronic receipt / order confirmation", rule_id="RCP-001",
                status="warning",
                found_value="Not confirmed from page content",
                recommendation="Requires manual verification: ensure receipts include date, merchant name, location, amount, card last 4 digits, and policy links.",
            ))

        # Add note about receipt requirements
        items.append(ChecklistItem(
            section=sec, item="Receipt content requirements (manual check needed)", rule_id="RCP-002",
            status="info",
            found_value="Cannot be fully verified by crawling",
            recommendation=(
                "Receipt must include: date/time, merchant name, Merchant Outlet Location, "
                "website URL, transaction type, product description, last 4 card digits, "
                "amount & currency, payment method, support contacts, links to T&C and Refund Policy."
            ),
        ))

        return items

    def _check_section_7(self) -> List[ChecklistItem]:
        sec = "7. Update Notification Requirements"
        return [ChecklistItem(
            section=sec, item="Notify ECOMMBX on changes", rule_id="UPD-001",
            status="info",
            found_value="Informational — cannot be verified by crawling",
            recommendation=(
                "You must notify ECOMMBX when changing: company name/registration, "
                "Merchant Outlet Location, license info, T&C (significant changes), "
                "business model, or adding other companies to the site."
            ),
        )]

    def _check_section_8(self, d: SiteContentExtraction) -> List[ChecklistItem]:
        sec = "8. Mobile Compliance"
        return [ChecklistItem(
            section=sec, item="Mobile-responsive design", rule_id="MOB-001",
            status="pass" if d.has_mobile_responsive else "warning",
            found_value="Responsive design detected" if d.has_mobile_responsive else "Not confirmed",
            recommendation=None if d.has_mobile_responsive else "Ensure mobile version meets the same compliance requirements.",
        )]

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _count_results(items: List[ChecklistItem]):
        scorable = [i for i in items if i.status in ("pass", "fail", "warning")]
        if not scorable:
            return (1, 1)  # informational section
        passed = sum(1 for i in scorable if i.status == "pass")
        return (passed, len(scorable))

    @staticmethod
    def _calculate_score(section_results: dict) -> int:
        score = 0.0
        for sec_id, (passed, total) in section_results.items():
            weight = SECTION_WEIGHTS.get(sec_id, 0)
            if total > 0:
                score += weight * (passed / total)
        return max(0, min(100, round(score)))
