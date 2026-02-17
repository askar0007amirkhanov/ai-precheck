from typing import Optional
from app.core.config import settings
from app.services.llm.client import LLMClient
import logging

logger = logging.getLogger(__name__)


class LLMFactory:
    _instances: dict[str, LLMClient] = {}

    @classmethod
    def get_client(cls, provider: str = None) -> LLMClient:
        """
        Get or create an LLM client instance.

        :param provider: 'openai', 'gemini', or 'mock'
        :return: Instance of LLMClient
        """
        provider = provider or settings.LLM_PROVIDER

        if provider in cls._instances:
            return cls._instances[provider]

        client: Optional[LLMClient] = None

        if provider == "mock":
            from app.services.llm.mock_client import MockClient
            logger.info("Using MockClient (demo mode)")
            client = MockClient()

        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set. Use LLM_PROVIDER=mock for demo mode.")
            from app.services.llm.openai_client import OpenAIClient
            client = OpenAIClient()

        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not set. Use LLM_PROVIDER=mock for demo mode.")
            from app.services.llm.gemini_client import GeminiClient
            client = GeminiClient()

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Use 'openai', 'gemini', or 'mock'.")

        cls._instances[provider] = client
        return client
