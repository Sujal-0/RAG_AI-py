"""SentenceTransformer implementation of the Embedding Provider."""

import logging
from typing import Any
from app.embeddings.providers.base import BaseEmbeddingProvider

logger = logging.getLogger("app")

class SentenceTransformerProvider(BaseEmbeddingProvider):
    """Provider for local HuggingFace SentenceTransformer models (e.g. BGE-M3)."""

    def __init__(self, model_name: str, dimension: int):
        super().__init__(model_name, dimension)
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model: %s ...", self.model_name)
            
            # Trust remote code is required for some advanced models like BGE-M3
            self._model = SentenceTransformer(self.model_name, trust_remote_code=True)
            
            logger.info(
                "SentenceTransformer model loaded successfully (dim=%d).",
                self.dimension,
            )
        except Exception as e:
            logger.error("Failed to load SentenceTransformer model %s: %s", self.model_name, e)
            raise

    def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        if not texts:
            return []
            
        vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=32, **kwargs)
        
        results = [v.tolist() for v in vectors]
        for v in results:
            if len(v) != self.dimension:
                logger.warning("Dimension mismatch: expected %d, got %d", self.dimension, len(v))
        return results

    def encode_single(self, text: str, **kwargs: Any) -> list[float]:
        vector = self._model.encode(text, normalize_embeddings=True, **kwargs)
        result = vector.tolist()
        if len(result) != self.dimension:
            logger.warning("Dimension mismatch: expected %d, got %d", self.dimension, len(result))
        return result
