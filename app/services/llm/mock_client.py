"""
Mock LLM Client for demo/testing purposes.
Returns deterministic data without calling any external API.
Activate via LLM_PROVIDER=mock in .env or environment variables.
"""
from typing import List, Type, Optional
from pydantic import BaseModel
from app.services.llm.client import LLMClient
import logging

logger = logging.getLogger(__name__)


class MockClient(LLMClient):
    """Deterministic mock client for testing and demo without real API keys."""

    async def extract_data(
        self,
        text: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> BaseModel:
        logger.info("MockClient: returning demo extraction data")
        return schema.model_validate({
            # Section 1: Company Information
            "company_name": "Demo Company Ltd",
            "registration_number": "12345678",
            "legal_address": "123 Demo Street, London, UK",
            "vat_number": "GB123456789",
            "merchant_outlet_location": "London, United Kingdom",
            "has_license_info": False,
            "license_number": None,
            "regulator_link": None,

            # Section 2: Contacts
            "support_email": "support@demo.com",
            "phone_number": "+44 20 1234 5678",
            "physical_address": "123 Demo Street, London, UK",
            "has_contact_page": True,

            # Section 3: Policies
            "has_terms_conditions": True,
            "has_privacy_policy": True,
            "has_refund_policy": True,
            "has_cancellation_policy": False,
            "has_payment_policy": False,
            "policies_accessible_from_all_pages": True,
            "policy_mentions_service_conditions": True,
            "policy_mentions_cancellation_terms": False,
            "policy_mentions_refund_terms": True,
            "refund_period_days": 14,
            "policy_mentions_user_restrictions": False,
            "policy_mentions_company_name": True,
            "site_primary_language": "English",

            # Section 4: Product/Service
            "has_product_description": True,
            "prices_in_purchase_currency": True,
            "all_fees_disclosed": True,
            "transparent_purchase_process": True,

            # Section 5: Checkout
            "shows_final_price": True,
            "shows_merchant_location_at_checkout": False,
            "has_terms_agreement_checkbox": True,

            # Section 6: Receipt
            "has_receipt_info": True,

            # Section 8: Mobile
            "has_mobile_responsive": True,

            # Extra
            "payment_methods_mentioned": ["Visa", "MasterCard", "PayPal"],
        })

    async def classify_text(
        self,
        text: str,
        labels: List[str],
        multi_label: bool = False,
    ) -> List[str]:
        logger.info("MockClient: returning first label as classification")
        return [labels[0]] if labels else []
