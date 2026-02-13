from typing import Optional
from app.core.config import settings
from app.services.llm.client import LLMClient
from app.services.llm.openai_client import OpenAIClient
from app.services.llm.gemini_client import GeminiClient

class LLMFactory:
    _instances: dict[str, LLMClient] = {}

    @classmethod
    def get_client(cls, provider: str = "openai") -> LLMClient:
        """
        Get or create an LLM client instance.
        
        :param provider: 'openai' or 'gemini'
        :return: Instance of LLMClient
        """
        if provider in cls._instances:
            return cls._instances[provider]

        client: Optional[LLMClient] = None

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set")
            client = OpenAIClient()
        
        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not set")
            client = GeminiClient()
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        cls._instances[provider] = client
        return client
