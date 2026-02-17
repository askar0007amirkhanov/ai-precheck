import json
import logging
from typing import List, Type, Optional

from pydantic import BaseModel
from google import genai
from google.genai import types

from app.core.config import settings
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)
        self.model_name = model

    async def extract_data(
        self,
        text: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> BaseModel:
        if not system_prompt:
            system_prompt = "You are a precise data extraction assistant. Extract the data strictly as JSON."

        logger.info("Gemini: sending extraction request to %s", self.model_name)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=f"{system_prompt}\n\nText:\n{text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0,
                ),
            )

            # SDK auto-parses JSON into the Pydantic model when response_schema is set
            if response.parsed is not None:
                logger.info("Gemini: extraction successful (parsed)")
                return response.parsed

            # Fallback: manual parsing if .parsed is None
            content = response.text.strip()
            logger.info("Gemini: parsing response manually (%d chars)", len(content))
            return schema.model_validate_json(content)

        except Exception as e:
            logger.error("Gemini extraction failed: %s", e, exc_info=True)
            raise RuntimeError(f"Gemini API call failed: {e}") from e

    async def classify_text(
        self,
        text: str,
        labels: List[str],
        multi_label: bool = False,
    ) -> List[str]:
        prompt = (
            f"Classify the following text into: {', '.join(labels)}.\n"
            f"{'Return ALL applicable labels.' if multi_label else 'Return exactly ONE label.'}\n"
            "Format: JSON object with key 'labels' containing a list of strings.\n"
            f"Text: {text}"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            content = response.text.strip()
            data = json.loads(content)
            return data.get("labels", [])

        except Exception as e:
            logger.error("Gemini classification failed: %s", e, exc_info=True)
            raise RuntimeError(f"Gemini API call failed: {e}") from e
