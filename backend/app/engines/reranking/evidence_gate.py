"""Evidence Gate Engine.

Acts as a strict quality filter for retrieved evidence. Rejects poor chunks 
and handles Neighbor Expansion to preserve context continuity.
"""

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentChunk
from app.engines.query.strategy_engine import RetrievalStrategy
from app.core.settings import settings

logger = logging.getLogger("app")


class EvidenceGate:
    """Filters evidence and expands neighboring context."""

    @classmethod
    async def filter_and_expand(
        cls, 
        session: AsyncSession,
        chunks: list[dict[str, Any]], 
        strategy: RetrievalStrategy
    ) -> list[dict[str, Any]]:
        
        valid_chunks = []
        rejected = 0

        # 1. Reject Poor Evidence
        for item in chunks:
            chunk = item["chunk"]
            score = item.get("rerank_score", 0.0)
            
            # Reject heading-only chunks (too short)
            if chunk.chunk_metadata.get("chunk_type") == "heading" and len(chunk.text) < 50:
                rejected += 1
                continue
                
            # Reject tiny chunks
            if len(chunk.text.split()) < settings.retrieval.minimum_chunk_size:
                rejected += 1
                continue
                
            # Reject low confidence chunks
            if score < settings.retrieval.weak_threshold:
                rejected += 1
                continue
                
            valid_chunks.append(item)

        # 2. Neighbor Expansion (Context Continuity)
        if strategy.expand_neighbors and valid_chunks:
            valid_chunks = await cls._expand_neighbors(session, valid_chunks)

        # Deduplicate
        final_list = []
        seen_ids = set()
        for item in valid_chunks:
            if item["chunk"].id not in seen_ids:
                final_list.append(item)
                seen_ids.add(item["chunk"].id)

        logger.info(
            "Evidence Gate Complete",
            extra={
                "structured_log": True, 
                "stage": "EvidenceGate", 
                "rejected_count": rejected,
                "final_count": len(final_list)
            }
        )
        
        if not final_list:
            raise ValueError("InsufficientEvidenceError")

        return final_list

    @classmethod
    async def _expand_neighbors(cls, session: AsyncSession, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fetch adjacent chunks (n-1, n+1) from the database."""
        
        expanded = []
        ids_to_fetch = set()
        
        for item in chunks:
            expanded.append(item)
            c = item["chunk"]
            # Rely on linked list IDs stored during semantic chunking
            prev_id = c.chunk_metadata.get("previous_chunk_id")
            next_id = c.chunk_metadata.get("next_chunk_id")
            
            if prev_id:
                ids_to_fetch.add(prev_id)
            if next_id:
                ids_to_fetch.add(next_id)
                
        if not ids_to_fetch:
            return expanded
            
        # Fetch neighbors
        stmt = select(DocumentChunk).where(DocumentChunk.id.in_(list(ids_to_fetch)))
        res = await session.execute(stmt)
        neighbors = res.scalars().all()
        
        for n in neighbors:
            expanded.append({
                "chunk": n,
                "rerank_score": 0.0, # Inherit 0 so they sort appropriately if needed, or link to parent
                "chunk_id": str(n.id)
            })
            
        return expanded
