"""LLM Enhancer Engine.

Utilizes a configured LLM Provider strictly to polish the grammar, readability, 
and flow of the Extractive Draft. 
If the LLM fails, falls back immediately to the deterministic Extractive Draft.
"""

import logging
from abc import ABC, abstractmethod
from app.generation.dto.dtos import ExtractiveDraft, PromptBundle, ResponsePlan

logger = logging.getLogger("app")


class BaseLLMEnhancer(ABC):
    @abstractmethod
    async def polish(self, draft: ExtractiveDraft, prompt: PromptBundle, plan: ResponsePlan) -> str:
        pass


class GeminiEnhancer(BaseLLMEnhancer):
    """Google Gemini specific implementation for language polishing."""
    
    async def polish(self, draft: ExtractiveDraft, prompt: PromptBundle, plan: ResponsePlan) -> str:
        logger.info("Polishing via Gemini", extra={"structured_log": True, "stage": "LLMEnhancer"})
        try:
            # Placeholder for actual google-genai call
            # response = await client.models.generate_content_async(model=..., contents=...)
            return draft.content
        except Exception as e:
            logger.error(f"Gemini polish failed: {e}. Falling back to draft.")
            return draft.content


class OpenAIEnhancer(BaseLLMEnhancer):
    """OpenAI specific implementation for language polishing."""
    
    async def polish(self, draft: ExtractiveDraft, prompt: PromptBundle, plan: ResponsePlan) -> str:
        logger.info("Polishing via OpenAI", extra={"structured_log": True, "stage": "LLMEnhancer"})
        return draft.content


class LLMEnhancerProviderFactory:
    """Dynamically loads the enhancer based on configuration."""
    
    _instance: BaseLLMEnhancer | None = None
    
    @classmethod
    def get_provider(cls, provider_name: str) -> BaseLLMEnhancer:
        if cls._instance is None:
            if provider_name.lower() == "openai":
                cls._instance = OpenAIEnhancer()
            else:
                cls._instance = GeminiEnhancer()
        return cls._instance
