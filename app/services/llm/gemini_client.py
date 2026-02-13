import json
import google.generativeai as genai
from typing import List, Type, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.services.llm.client import LLMClient

class GeminiClient(LLMClient):
    def __init__(self, api_key: str = settings.GEMINI_API_KEY, model: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model_name = model

    async def extract_data(
        self, 
        text: str, 
        schema: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        model = genai.GenerativeModel(self.model_name)
        
        prompt = (
            f"{system_prompt or 'Extract data from the text.'}\n"
            f"Output must be valid JSON matching this schema: {schema.model_json_schema()}\n"
            f"Text: {text}"
        )
        
        # Gemini does not have strict JSON mode enforced via API param in basic SDK yet (as of v0.3.2 purely),
        # but robust prompting usually works. For production, we might want to use stricter parsing or specialized tools.
        response = await model.generate_content_async(prompt)
        
        # Simple cleanup to ensure JSON parsing
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return schema.model_validate_json(content)

    async def classify_text(
        self, 
        text: str, 
        labels: List[str], 
        multi_label: bool = False
    ) -> List[str]:
        model = genai.GenerativeModel(self.model_name)
        
        prompt = (
            f"Classify the text into: {', '.join(labels)}.\n"
            f"{'Return ALL applicable labels' if multi_label else 'Return exactly ONE label'}.\n"
            "Format: JSON object with key 'labels' (list of strings).\n"
            f"Text: {text}"
        )
        
        response = await model.generate_content_async(prompt)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        
        data = json.loads(content)
        return data.get("labels", [])
