"""Embedding service for semantic vector generation.

Acts as a Provider Factory, managing lazy-loading and execution of embedding models
via the configured provider interface.
"""

import logging
from typing import Any

from app.core.settings import settings
from app.embeddings.providers.base import BaseEmbeddingProvider
from app.embeddings.providers.sentence_transformer import SentenceTransformerProvider

logger = logging.getLogger("app")


class EmbeddingService:
    """Manages lazy-loading and execution of the embedding model provider."""

    _provider: BaseEmbeddingProvider | None = None
    
    # Expose these for legacy compatibility temporarily
    model_name: str = settings.embedding.model
    dimension: int = settings.embedding.dimension

    @classmethod
    def get_provider(cls) -> BaseEmbeddingProvider:
        """Initialize and retrieve the cached embedding provider (singleton)."""
        if cls._provider is not None:
            return cls._provider

        model_name = settings.embedding.model
        dimension = settings.embedding.dimension

        logger.info("Initializing Embedding Provider for model: %s", model_name)
        
        # Currently defaults to SentenceTransformerProvider for models like BGE-M3 and MiniLM.
        # This factory pattern allows easy swapping to VoyageAIProvider, OpenAIProvider, etc.
        try:
            cls._provider = SentenceTransformerProvider(model_name=model_name, dimension=dimension)
        except Exception as e:
            logger.critical("Failed to initialize Embedding Provider: %s", e)
            raise

        return cls._provider

    @classmethod
    def generate_embedding(cls, text: str) -> list[float]:
        """Generate a dense vector embedding for a single text string."""
        provider = cls.get_provider()
        try:
            return provider.encode_single(text)
        except Exception as e:
            logger.error("Failed to generate embedding for text: %s", e)
            raise

    @classmethod
    def generate_embeddings(cls, texts: list[str]) -> list[list[float]]:
        """Generate embeddings in batch for a list of text strings."""
        if not texts:
            return []

        provider = cls.get_provider()
        try:
            return provider.encode(texts)
        except Exception as e:
            logger.error("Failed to generate batch embeddings: %s", e)
            raise

    @classmethod
    def reset(cls) -> None:
        """Reset provider state — used for testing and re-initialization."""
        cls._provider = None

    @classmethod
    async def background_reindex_worker(cls) -> None:
        """Background worker to automatically detect and re-index stale documents."""
        try:
            import asyncio
            from app.api.reindex import _reindex_all_documents
            from app.api.reindex import reindex_status_endpoint
            
            logger.info("Background re-index worker started. Checking for stale embeddings...")
            
            status = await reindex_status_endpoint()
            if status.get("reindex_needed"):
                logger.info(f"Found {status.get('outdated_versions')} outdated documents. Re-indexing...")
                result = await _reindex_all_documents()
                
                success = result.get('success_count', 0)
                errors = result.get('error_count', 0)
                logger.info(f"Re-indexing complete. Success: {success}, Errors: {errors}")
            else:
                logger.info("No stale embeddings found. All documents are up to date.")
        except Exception as e:
            logger.error(f"Background re-index worker failed: {e}")
