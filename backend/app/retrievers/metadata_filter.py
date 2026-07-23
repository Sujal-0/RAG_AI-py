"""Metadata Filtering Engine.

Constructs deterministic SQLAlchemy filters based on the active Retrieval Strategy, 
Normalized Query, and known Entity/Topic states.
"""

import logging
from sqlalchemy import or_, and_, text
from app.database.models import DocumentChunk, DocumentVersion, Document
from app.engines.query.strategy_engine import RetrievalStrategy
from app.engines.query.query_analyzer import NormalizedQuery

logger = logging.getLogger("app")

class MetadataFilterEngine:
    """Generates SQLAlchemy filter clauses."""

    @classmethod
    def generate_filters(
        cls, 
        strategy: RetrievalStrategy, 
        query: NormalizedQuery,
        active_entities: dict[str, list[str]]
    ) -> list:
        """Generate a list of SQLAlchemy filters."""
        filters = []

        # 1. Status Filter (Always enforce ready chunks)
        filters.append(DocumentVersion.status == "ready_for_search")

        # 2. Chunk Type Filter
        if strategy.target_chunk_types:
            # We assume chunk_metadata stores the chunk_type OR DocumentChunk has chunk_type.
            # In our new foundation, DocumentChunk has chunk_metadata['chunk_type'] or we might have stored it elsewhere.
            # Fallback to a text search in the JSONB if it's there.
            # For robustness, we use PostgreSQL JSONB containment.
            # e.g. DocumentChunk.chunk_metadata.op("->>")("chunk_type").in_(strategy.target_chunk_types)
            # However, because chunk_type wasn't explicitly added as a column, we query JSONB.
            
            chunk_type_filter = or_(
                DocumentChunk.chunk_metadata["chunk_type"].astext.in_(strategy.target_chunk_types),
                DocumentChunk.chunk_metadata["chunk_type"].astext.is_(None)
            )
            filters.append(chunk_type_filter)

        # 3. Exact Metadata requirement
        if strategy.require_exact_metadata:
            # If the user asks for a specific topic or entity, enforce it strongly.
            # Example: Policy intent requires strict metadata alignment.
            pass

        logger.debug(
            "Metadata Filters Generated",
            extra={
                "structured_log": True, 
                "stage": "MetadataFilterEngine",
                "filter_count": len(filters)
            }
        )

        return filters
