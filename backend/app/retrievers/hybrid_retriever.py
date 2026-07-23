"""Hybrid Retriever (Reciprocal Rank Fusion).

Combines Sparse and Dense results using RRF. This produces a highly robust
retrieval set that benefits from both exact keyword matches and semantic meaning.
"""

import logging
from typing import Any
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.engines.query.query_analyzer import NormalizedQuery
from app.engines.query.strategy_engine import RetrievalStrategy
from app.core.settings import settings
from app.database.models import DocumentChunk
from app.embeddings.embedding_service import EmbeddingService
from app.engines.providers.factories import RerankerProviderFactory

logger = logging.getLogger("app")

class HybridRetriever:
    """Executes ultra-fast pgvector HNSW direct query and Cross-Encoder reranking."""

    @classmethod
    async def retrieve(
        cls, 
        session: AsyncSession,
        original_query: NormalizedQuery,
        rewritten_query: str,
        strategy: RetrievalStrategy,
        metadata_filters: list,
        top_k: int = 15
    ) -> list[dict[str, Any]]:
        """Run pgvector HNSW with Cross-Encoder reranking."""
        
        logger.info(
            "Executing HNSW + Cross-Encoder Fast-Fetch",
            extra={"structured_log": True, "stage": "HybridRetriever"}
        )

        # 1. Generate query embedding
        query_vector = await asyncio.to_thread(EmbeddingService.generate_embedding, rewritten_query)
        
        # 2. PGVector HNSW Cosine Similarity Lookup
        stmt = (
            select(DocumentChunk)
            .order_by(DocumentChunk.embedding_vector.cosine_distance(query_vector))
            .limit(top_k)
        )
        
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        retrieved_chunks = [
            {
                "chunk_id": str(c.id),
                "chunk": c.text,
                "metadata": c.chunk_metadata,
                "document_id": c.chunk_metadata.get("document_id", ""),
                "dense_score": 1.0, # Placeholder for downstream compatibility
                "db_chunk": c
            } for c in chunks
        ]
        
        if not retrieved_chunks:
            return []

        # 3. Cross-Encoder Reranking
        reranker = RerankerProviderFactory.get_provider()
        reranked_chunks = await asyncio.to_thread(
            reranker.rerank,
            rewritten_query, 
            retrieved_chunks, 
            top_k
        )
        
        # 4. Truncation
        baseline = settings.retrieval.minimum_similarity
        
        valid_chunks = [
            c for c in reranked_chunks 
            if c.get("rerank_score", c.get("score", 0.0)) >= baseline
        ]
        
        final_evidence = valid_chunks[:4]
        
        logger.info(
            "Hybrid Fast-Fetch Complete",
            extra={"structured_log": True, "stage": "HybridRetriever", "returned_count": len(final_evidence)}
        )
            
        return final_evidence
