from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

class LLMClient(ABC):
    """
    Abstract Base Class for LLM Providers.
    Enforces a strict interface for extraction and classification to avoid vendor lock-in.
    """

    @abstractmethod
    async def extract_data(
        self, 
        text: str, 
        schema: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        """
        Extract structured data from unstructured text matching a Pydantic schema.
        
        :param text: Cleaned input text (NO RAW HTML).
        :param schema: Pydantic model class defining the output structure.
        :param system_prompt: Optional override for system instructions.
        :return: Instance of the schema model.
        """
        pass

    @abstractmethod
    async def classify_text(
        self, 
        text: str, 
        labels: List[str], 
        multi_label: bool = False
    ) -> List[str]:
        """
        Classify text into one or more predefined labels.
        
        :param text: Input text.
        :param labels: List of allowed labels.
        :param multi_label: Whether multiple labels can be returned.
        :return: List of valid labels applied to the text.
        """
        pass
