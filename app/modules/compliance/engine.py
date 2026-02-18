from datetime import datetime, timezone
from typing import List
from app.modules.compliance.schemas import (
    ComplianceReport, ChecklistItem, SiteContentExtraction,
    DynamicChecklistRule, DynamicExtractionResult
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
    def __init__(self, llm_provider: str = None, model: str = None):
        self.provider = llm_provider or settings.LLM_PROVIDER
        self.llm_client = LLMFactory.get_client(self.provider, model=model)

    async def analyze_site(self, clean_text: str) -> ComplianceReport:
        """
        Analyze cleaned website text against the full ECOMMBX compliance checklist.
        Uses LLM for data extraction, then applies deterministic rules.
        """
        # 1. Extract data via LLM
        system_prompt = (
            "You are an expert compliance analyst for ECOMMBX payment processing. "
            "Your task is to extract specific regulatory and compliance information "
            "from a merchant website. Be strict, factual, and conservative:\n\n"

            "SECTION 1 — COMPANY INFORMATION:\n"
            "- company_name: The full LEGAL entity name (e.g. 'ABC Ltd', 'XYZ LLC'). "
            "Look in footer, About Us, Terms & Conditions, or legal pages. "
            "Do NOT use brand/trade names unless they ARE the legal name.\n"
            "- registration_number: Company registration / incorporation number "
            "(e.g. 'HE 12345', 'Company No. 789'). Often found in footer or legal pages.\n"
            "- legal_address: The company's REGISTERED address for legal purposes. "
            "Usually found in Terms & Conditions or footer.\n"
            "- vat_number: VAT / tax ID (e.g. 'CY10012345A', 'GB123456789').\n"
            "- merchant_outlet_location: The PHYSICAL place where the business operates. "
            "This may differ from legal address. Look for office address, location.\n"
            "- has_license_info: true ONLY if there is a mention of a regulatory license, "
            "regulator name, or license number.\n"
            "- license_number: The actual license number if mentioned.\n"
            "- regulator_link: Name or URL of the regulatory authority.\n\n"

            "SECTION 2 — CONTACTS:\n"
            "- support_email: A support/contact email address (e.g. support@, info@, contact@).\n"
            "- phone_number: A contact phone number with country code if available.\n"
            "- physical_address: A mailing or office address for correspondence.\n"
            "- has_contact_page: true if there is a 'Contact Us', 'Contact', or 'Support' page/section.\n\n"

            "SECTION 3 — POLICIES:\n"
            "- has_terms_conditions: true if there is a 'Terms & Conditions', 'Terms of Service', "
            "or 'Terms of Use' page or link.\n"
            "- has_privacy_policy: true if there is a 'Privacy Policy' or 'Data Protection Policy' page or link.\n"
            "- has_refund_policy: true if there is a 'Refund Policy', 'Return Policy', "
            "or 'Money Back Guarantee' page or link.\n"
            "- has_cancellation_policy: true if there is a 'Cancellation Policy' or a section "
            "about cancelling orders/subscriptions.\n"
            "- has_payment_policy: true if there is a 'Payment Policy', 'Billing Policy', "
            "or detailed payment terms page.\n"
            "- policies_accessible_from_all_pages: true if policy links appear in the "
            "footer, sidebar, or navigation menu (accessible site-wide).\n"
            "- policy_mentions_service_conditions: true if the policies describe what services are provided, "
            "how they work, or conditions of sale.\n"
            "- policy_mentions_cancellation_terms: true if cancellation rules are described anywhere in policies.\n"
            "- policy_mentions_refund_terms: true if refund/return deadlines, process, or conditions are described.\n"
            "- refund_period_days: The number of days allowed for refunds (e.g. 14, 30). "
            "null if not mentioned.\n"
            "- policy_mentions_user_restrictions: true if there are any restrictions "
            "(age, geography, prohibited uses).\n"
            "- policy_mentions_company_name: true if the legal company name is explicitly stated "
            "in the Terms or other policies as the contracting party.\n"
            "- site_primary_language: The primary language of the website content "
            "(e.g. 'English', 'Russian', 'Arabic').\n\n"

            "SECTION 4 — PRODUCT/SERVICE DESCRIPTION:\n"
            "- has_product_description: true if products or services are described "
            "with details (not just a name/title).\n"
            "- prices_in_purchase_currency: true if prices are shown with a clear currency symbol or code.\n"
            "- all_fees_disclosed: true if all fees, taxes, shipping, and extra charges are listed.\n"
            "- transparent_purchase_process: true if the buying flow is clear (add to cart → checkout → pay).\n\n"

            "SECTION 5 — CHECKOUT:\n"
            "- shows_final_price: true if there is evidence of a final total being shown before payment.\n"
            "- shows_merchant_location_at_checkout: true if the merchant location is displayed during checkout.\n"
            "- has_terms_agreement_checkbox: true if there is a checkbox to agree to "
            "Terms & Conditions before completing a purchase.\n\n"

            "SECTION 6 — RECEIPT:\n"
            "- has_receipt_info: true if there is any mention of order confirmations, "
            "email receipts, or transaction receipts.\n\n"

            "SECTION 8 — MOBILE:\n"
            "- has_mobile_responsive: true if there is evidence of responsive design "
            "(viewport meta tag, media queries, mobile menu).\n\n"

            "EXTRA:\n"
            "- payment_methods_mentioned: List ALL payment methods (Visa, Mastercard, "
            "PayPal, Crypto, bank transfer, etc.).\n\n"

            "RULES:\n"
            "- Return false/null if you are NOT confident the information is present.\n"
            "- Do NOT infer or guess — only extract what is explicitly stated.\n"
            "- Err on the side of false/null rather than making assumptions."
        )

        extracted: SiteContentExtraction = await self.llm_client.extract_data(
            text=clean_text[:50000],
            schema=SiteContentExtraction,
            system_prompt=system_prompt,
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

    async def analyze_dynamic(self, clean_text: str, rules: List[DynamicChecklistRule]) -> ComplianceReport:
        """
        Analyze site using a dynamic set of rules (e.g. from uploaded checklist).
        """
        if not rules:
            return ComplianceReport(score=0, status="NEEDS_REVIEW", summary="No rules provided.")

        # 1. Build Dynamic Prompt
        system_prompt = (
            "You are a compliance checking agent. "
            "Your goal is to extract specific information from the website text based on a list of rules.\n"
            "For each rule ID, extract the relevant content found on the page.\n"
            "If information is NOT found, return 'Not found'.\n"
            "Be strict and factual.\n\n"
            "RULES TO CHECK:\n"
        )
        
        for r in rules:
            system_prompt += f"- {r.rule_id} ({r.item}): {r.extraction_prompt}\n"

        # 2. Extract
        try:
            extracted: DynamicExtractionResult = await self.llm_client.extract_data(
                text=clean_text[:50000],
                schema=DynamicExtractionResult,
                system_prompt=system_prompt,
            )
        except Exception as e:
            logger.error(f"Dynamic extraction failed: {e}")
            # Fallback empty result
            extracted = DynamicExtractionResult(results={})

        # 3. Evaluate & Build Checklist
        checklist: List[ChecklistItem] = []
        passed_count = 0
        total_count = 0

        for r in rules:
            val = extracted.results.get(r.rule_id, "Not found")
            is_pass = False
            
            # Simple evaluation logic
            condition = r.pass_condition.lower()
            val_lower = str(val).lower().strip()
            
            if val_lower in ["not found", "none", "", "null"]:
                is_pass = False
            elif condition == "not_empty":
                is_pass = True
            elif condition == "true":
                is_pass = val_lower in ["true", "yes", "found", "present"]
            elif "contains" in condition:
                # e.g. "contains(privacy)"
                target = condition.replace("contains(", "").replace(")", "").strip()
                is_pass = target in val_lower
            else:
                # Default fallback: if we found something not "Not found", it passes
                is_pass = True

            status = "pass" if is_pass else r.severity
            if status != "info":
                total_count += 1
                if status == "pass":
                    passed_count += 1
            
            checklist.append(ChecklistItem(
                section=r.section,
                item=r.item,
                rule_id=r.rule_id,
                status=status,
                found_value=str(val)[:100], # Truncate for display
                recommendation=None if is_pass else r.description
            ))

        # 4. Report
        score = int((passed_count / total_count) * 100) if total_count > 0 else 0
        status = "COMPLIANT" if score == 100 else "NON-COMPLIANT"
        
        return ComplianceReport(
            company_name="Dynamic Check", # We might need a separate rule to extract company name specifically
            score=score,
            status=status,
            checklist=checklist,
            summary=f"Dynamic check: {passed_count}/{total_count} rules passed.",
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
