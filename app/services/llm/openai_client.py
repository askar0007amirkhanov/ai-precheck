import json
from typing import List, Type, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.llm.client import LLMClient

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str = settings.OPENAI_API_KEY, model: str = "gpt-4-turbo-preview"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def extract_data(
        self, 
        text: str, 
        schema: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        # Mock Handling for Demo
        if "mock" in self.client.api_key.lower() or "demo" in text.lower():
            return schema.model_validate({
                "company_name": "Demo Company",
                "has_privacy_policy": True,
                "has_terms_of_service": False,
                "has_refund_policy": True,
                "refund_period_days": 14,
                "has_contact_details": True,
                "payment_methods_mentioned": ["Visa", "MasterCard"]
            })

        if not system_prompt:
            system_prompt = "You are a precise data extraction assistant. Extract the data strictly as JSON."

        completion = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{system_prompt}. Output strictly adhering to this JSON schema: {schema.model_json_schema()}"},
                {"role": "user", "content": text}
            ]
        )
        
        content = completion.choices[0].message.content
        return schema.model_validate_json(content)

    async def classify_text(
        self, 
        text: str, 
        labels: List[str], 
        multi_label: bool = False
    ) -> List[str]:
        # Mock Handling for Demo
        if "mock" in self.client.api_key.lower():
            return [labels[0]]

        system_prompt = (
            f"Classify the following text into one of these categories: {', '.join(labels)}."
            f"{' Return ALL applicable labels.' if multi_label else ' Return exactly ONE label.'}"
            " Return result as a JSON object with a single key 'labels' containing a list of strings."
        )

        completion = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )

        content = completion.choices[0].message.content
        data = json.loads(content)
        return data.get("labels", [])
