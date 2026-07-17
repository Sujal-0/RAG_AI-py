"""Base Provider Interface for embedding models."""

from abc import ABC, abstractmethod
from typing import Any

class BaseEmbeddingProvider(ABC):
    """Abstract interface for all embedding providers."""

    @abstractmethod
    def __init__(self, model_name: str, dimension: int):
        self.model_name = model_name
        self.dimension = dimension

    @abstractmethod
    def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def encode_single(self, text: str, **kwargs: Any) -> list[float]:
        """Generate embedding for a single text string."""
        pass
