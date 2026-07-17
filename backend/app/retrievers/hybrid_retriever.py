"""Hybrid Retriever (Reciprocal Rank Fusion).

Combines Sparse and Dense results using RRF. This produces a highly robust
retrieval set that benefits from both exact keyword matches and semantic meaning.
"""

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.query.query_analyzer import NormalizedQuery
from app.engines.query.strategy_engine import RetrievalStrategy
from app.retrievers.keyword_retriever import KeywordRetriever
from app.retrievers.dense_retriever import DenseRetriever
from app.core.settings import settings

logger = logging.getLogger("app")


class HybridRetriever:
    """Executes Dense and Sparse retrieval and fuses the results."""

    @classmethod
    async def retrieve(
        cls, 
        session: AsyncSession,
        original_query: NormalizedQuery,
        rewritten_query: str,
        strategy: RetrievalStrategy,
        metadata_filters: list,
        top_k: int = 40
    ) -> list[dict[str, Any]]:
        """Run Hybrid Retrieval with RRF."""
        
        logger.info(
            "Executing Hybrid Retrieval",
            extra={"structured_log": True, "stage": "HybridRetriever"}
        )

        # Execute both retrievers (ideally concurrently using asyncio.gather)
        import asyncio
        sparse_task = KeywordRetriever.retrieve(session, original_query, strategy, metadata_filters, top_k)
        dense_task = DenseRetriever.retrieve(session, rewritten_query, strategy, metadata_filters, top_k)
        
        sparse_results, dense_results = await asyncio.gather(sparse_task, dense_task)
        
        return cls._fuse_results_rrf(sparse_results, dense_results, top_k)

    @classmethod
    def _fuse_results_rrf(
        cls, 
        sparse_results: list[dict[str, Any]], 
        dense_results: list[dict[str, Any]],
        top_k: int
    ) -> list[dict[str, Any]]:
        """Apply Reciprocal Rank Fusion."""
        
        fused_scores = {}
        chunk_map = {}
        
        # Rank sparse
        for rank, item in enumerate(sparse_results):
            cid = item["chunk_id"]
            chunk_map[cid] = item["chunk"]
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (settings.retrieval.rrf_constant + rank + 1))
            
        # Rank dense
        for rank, item in enumerate(dense_results):
            cid = item["chunk_id"]
            if cid not in chunk_map:
                chunk_map[cid] = item["chunk"]
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (settings.retrieval.rrf_constant + rank + 1))
            
        # Sort by fused score descending
        sorted_cids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        
        final_results = []
        for cid in sorted_cids[:top_k]:
            final_results.append({
                "chunk": chunk_map[cid],
                "hybrid_score": fused_scores[cid],
                "chunk_id": cid
            })
            
        logger.info(
            "Hybrid Fusion Complete",
            extra={"structured_log": True, "stage": "HybridRetriever", "fused_count": len(final_results)}
        )
            
        return final_results
