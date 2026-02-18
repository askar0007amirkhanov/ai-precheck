from typing import Optional
from app.core.config import settings
from app.services.llm.client import LLMClient
import logging

logger = logging.getLogger(__name__)


class LLMFactory:
    _instances: dict[str, LLMClient] = {}

    @classmethod
    def get_client(cls, provider: str = None, model: str = None) -> LLMClient:
        """
        Get or create an LLM client instance.

        :param provider: 'openai', 'gemini', or 'mock'
        :param model: Optional model name (e.g. 'gemini-2.5-flash', 'gemini-2.5-pro')
        :return: Instance of LLMClient
        """
        provider = provider or settings.LLM_PROVIDER

        # Cache key includes model for provider-specific model selection
        cache_key = f"{provider}:{model}" if model else provider

        if cache_key in cls._instances:
            return cls._instances[cache_key]

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
            if model:
                logger.info("Creating GeminiClient with model: %s", model)
                client = GeminiClient(model=model)
            else:
                client = GeminiClient()

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Use 'openai', 'gemini', or 'mock'.")

        cls._instances[cache_key] = client
        return client

