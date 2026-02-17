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
            "company_name": "Demo Company",
            "has_privacy_policy": True,
            "has_terms_of_service": False,
            "has_refund_policy": True,
            "refund_period_days": 14,
            "has_contact_details": True,
            "payment_methods_mentioned": ["Visa", "MasterCard"],
            "privacy_policy_mentions_gdpr": False,
        })

    async def classify_text(
        self,
        text: str,
        labels: List[str],
        multi_label: bool = False,
    ) -> List[str]:
        logger.info("MockClient: returning first label as classification")
        return [labels[0]] if labels else []
