"""Dense Retriever (Semantic Search).

Executes pgvector semantic search using the dynamic Embedding Provider.
Supports configurable distances, limits, and thresholds.
"""

import logging
from typing import Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentChunk, DocumentVersion
from app.engines.query.query_analyzer import NormalizedQuery
from app.engines.query.strategy_engine import RetrievalStrategy
from app.embeddings.embedding_service import EmbeddingService

logger = logging.getLogger("app")


class DenseRetriever:
    """pgvector Dense Retriever."""

    @classmethod
    async def retrieve(
        cls, 
        session: AsyncSession,
        query: str, # Usually the rewritten query
        strategy: RetrievalStrategy,
        metadata_filters: list,
        top_k: int = 40
    ) -> list[dict[str, Any]]:
        """Execute pgvector dense search."""
        
        logger.info(
            "Executing Dense Search",
            extra={"structured_log": True, "stage": "DenseRetriever"}
        )

        try:
            # 1. Generate query embedding
            query_vector = EmbeddingService.generate_embedding(query)
            
            # 2. Vector distance (Cosine distance in pgvector is <=> )
            # We want to order by cosine distance ascending (closest first)
            # Similarity = 1 - distance
            distance = DocumentChunk.embedding_vector.cosine_distance(query_vector).label("distance")
            
            stmt = (
                select(DocumentChunk, distance)
                .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
                .where(*metadata_filters)
                .order_by(distance)
                .limit(top_k)
            )
            
            res = await session.execute(stmt)
            results = []
            
            for chunk, dist in res.all():
                similarity = 1.0 - float(dist)
                results.append({
                    "chunk": chunk,
                    "dense_score": similarity,
                    "chunk_id": str(chunk.id)
                })
                
            logger.info(
                "Dense Search Complete",
                extra={"structured_log": True, "stage": "DenseRetriever", "retrieved_count": len(results)}
            )
            return results

        except Exception as e:
            logger.error(f"Dense Retrieval Failed: {e}")
            return []
