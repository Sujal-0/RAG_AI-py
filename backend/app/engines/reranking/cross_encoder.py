"""Cross Encoder Reranker Engine.

Re-ranks the Top 40 candidates from the Hybrid Retriever using a cross-encoder 
model (like BAAI/bge-reranker-v2-m3) to compute exact semantic interaction between 
the query and the chunk text.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("app")


class BaseRerankerProvider(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        pass


class SentenceTransformerReranker(BaseRerankerProvider):
    """Local provider for Cross-Encoder models."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading CrossEncoder: {self.model_name} ...")
            # trust_remote_code required for BGE models
            self.model = CrossEncoder(self.model_name, trust_remote_code=True)
            logger.info("CrossEncoder loaded successfully.")
        except ImportError:
            logger.warning("SentenceTransformers not installed. Reranking will be a pass-through.")
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder: {e}")

    def rerank(self, query: str, chunks: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        if not self.model or not chunks:
            return chunks[:top_k]

        # Prepare pairs: (query, chunk_text)
        pairs = [(query, item["chunk"].text) for item in chunks]

        # Predict scores
        try:
            scores = self.model.predict(pairs)
            
            # Attach scores
            for item, score in zip(chunks, scores):
                # BGE reranker outputs logits, can be converted to probabilities or used raw
                item["rerank_score"] = float(score)

            # Sort by rerank score descending
            reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
            
            logger.info(
                "Reranking Complete",
                extra={"structured_log": True, "stage": "CrossEncoder", "input_count": len(chunks), "output_count": top_k}
            )
            
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return chunks[:top_k]
