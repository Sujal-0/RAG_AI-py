"""Keyword Retriever (Sparse Retrieval).

Executes BM25 / Full Text Search against PostgreSQL using `tsvector`.
Highly effective for exact term matches, acronyms, and product codes.
"""

import logging
from typing import Any
from sqlalchemy import select, func, text, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentChunk, DocumentVersion
from app.engines.query.query_analyzer import NormalizedQuery
from app.engines.query.strategy_engine import RetrievalStrategy

logger = logging.getLogger("app")


class KeywordRetriever:
    """PostgreSQL FTS Retriever."""

    @classmethod
    async def retrieve(
        cls, 
        session: AsyncSession,
        query: NormalizedQuery, 
        strategy: RetrievalStrategy,
        metadata_filters: list,
        top_k: int = 40
    ) -> list[dict[str, Any]]:
        """Execute sparse FTS search."""
        
        # We use standard english tsvector. 
        # In a real environment, we'd add an indexed tsvector column to the chunk table.
        # Here we compute it dynamically or rely on GiST/GIN if created.
        
        search_query = query.normalized_text
        if query.abbreviations:
            search_query += " " + " ".join(query.abbreviations)
            
        logger.info(
            "Executing Keyword Search (FTS)",
            extra={"structured_log": True, "stage": "KeywordRetriever", "search_text": search_query}
        )

        # Construct FTS logic
        # ts_rank computes the BM25-like score
        tsquery = func.websearch_to_tsquery('english', search_query)
        tsvector = func.to_tsvector('english', DocumentChunk.text)
        rank = func.ts_rank(tsvector, tsquery).label("sparse_score")

        stmt = (
            select(DocumentChunk, rank)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(tsvector.op('@@')(tsquery))
            .where(*metadata_filters)
            .order_by(desc(rank))
            .limit(top_k)
        )

        try:
            res = await session.execute(stmt)
            results = []
            for chunk, score in res.all():
                results.append({
                    "chunk": chunk,
                    "sparse_score": float(score),
                    "chunk_id": str(chunk.id)
                })
                
            logger.info(
                "Keyword Search Complete",
                extra={"structured_log": True, "stage": "KeywordRetriever", "retrieved_count": len(results)}
            )
            return results
            
        except Exception as e:
            logger.error(f"FTS Retrieval Failed: {e}")
            return []
