"""Retrieval Orchestrator.

The exclusive public entry point for the Retrieval Engine. 
Coordinates the 10-stage pipeline, managing dependencies, correlation IDs, 
structured logging, and timing metrics across all execution phases.
"""

import logging
import time
import uuid
from typing import Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.engines.query.query_analyzer import QueryAnalyzer, NormalizedQuery
from app.engines.query.intent_detector import IntentDetectionEngine
from app.engines.query.conversation_resolver import ConversationResolver, ConversationState
from app.engines.query.strategy_engine import RetrievalStrategyEngine, RetrievalStrategy

from app.engines.providers.factories import (
    EntityProviderFactory, 
    KeywordProviderFactory, 
    QueryRewriteProviderFactory,
    RerankerProviderFactory
)

from app.retrievers.metadata_filter import MetadataFilterEngine
from app.retrievers.dense_retriever import DenseRetriever
from app.retrievers.keyword_retriever import KeywordRetriever
from app.retrievers.hybrid_retriever import HybridRetriever
from app.engines.reranking.evidence_gate import EvidenceGate
from app.engines.reranking.confidence_engine import ConfidenceEngine

logger = logging.getLogger("app")


@dataclass
class RetrievalResult:
    """Strongly typed output of the Retrieval Pipeline."""
    trace_id: str
    original_query: str
    normalized_query: NormalizedQuery
    rewritten_query: str
    intent: str
    strategy: RetrievalStrategy
    evidence: list[dict[str, Any]]
    confidence: str
    confidence_score: float
    metrics: dict[str, Any]


class RetrievalOrchestrator:
    """Coordinates the end-to-end retrieval process."""

    @classmethod
    async def execute(
        cls, 
        session: AsyncSession, 
        raw_query: str, 
        session_history: list[dict[str, str]]
    ) -> RetrievalResult:
        """Execute the full retrieval pipeline."""
        
        trace_id = str(uuid.uuid4())
        metrics = {"total_duration_ms": 0}
        total_start = time.time()
        
        logger.info(
            "Starting Retrieval Pipeline",
            extra={"structured_log": True, "trace_id": trace_id, "stage": "Orchestrator", "query": raw_query}
        )

        try:
            # Phase 1: Query Analysis
            start = time.time()
            normalized_query = QueryAnalyzer.analyze(raw_query)
            metrics["query_analyzer_ms"] = int((time.time() - start) * 1000)

            # Extract Entities
            start = time.time()
            entity_provider = EntityProviderFactory.get_provider()
            active_entities = entity_provider.extract(normalized_query.normalized_text)
            metrics["entity_extraction_ms"] = int((time.time() - start) * 1000)

            # Extract Keywords
            start = time.time()
            keyword_provider = KeywordProviderFactory.get_provider()
            keywords = keyword_provider.extract(normalized_query.normalized_text)
            metrics["keyword_extraction_ms"] = int((time.time() - start) * 1000)

            # Detect Intent
            start = time.time()
            intent = IntentDetectionEngine.detect_intent(normalized_query.normalized_text)
            metrics["intent_detection_ms"] = int((time.time() - start) * 1000)

            # Phase 2: Conversation Resolution & Rewrite
            start = time.time()
            conv_state = ConversationResolver.resolve_state(
                raw_query, session_history, active_entities
            )
            rewrite_provider = QueryRewriteProviderFactory.get_provider()
            rewritten_query = await rewrite_provider.rewrite(raw_query, conv_state)
            metrics["conversation_ms"] = int((time.time() - start) * 1000)

            # Phase 3: Strategy Engine
            strategy = RetrievalStrategyEngine.determine_strategy(
                intent, normalized_query.response_expectation
            )

            # Phase 4: Metadata Filtering
            filters = MetadataFilterEngine.generate_filters(
                strategy, normalized_query, active_entities
            )

            # Phase 5 & 6 & 7: Execution (Dense/Sparse/Hybrid)
            start = time.time()
            if settings.retrieval.hybrid_enabled:
                retrieved_chunks = await HybridRetriever.retrieve(
                    session,
                    original_query=normalized_query,
                    rewritten_query=rewritten_query,
                    strategy=strategy,
                    metadata_filters=filters,
                    top_k=settings.retrieval.top_k_hybrid
                )
            else:
                # Fallback to pure dense
                retrieved_chunks = await DenseRetriever.retrieve(
                    session, rewritten_query, strategy, filters, settings.retrieval.top_k_dense
                )
            metrics["retrieval_execution_ms"] = int((time.time() - start) * 1000)
            metrics["retrieved_count"] = len(retrieved_chunks)

            # Phase 8: Cross Encoder Reranking
            start = time.time()
            reranker = RerankerProviderFactory.get_provider()
            reranked_chunks = reranker.rerank(
                rewritten_query, 
                retrieved_chunks, 
                top_k=settings.retrieval.top_k_rerank
            )
            metrics["reranking_ms"] = int((time.time() - start) * 1000)

            # Phase 9: Evidence Gate
            start = time.time()
            final_evidence = await EvidenceGate.filter_and_expand(
                session, reranked_chunks, strategy
            )
            metrics["evidence_gate_ms"] = int((time.time() - start) * 1000)
            metrics["final_evidence_count"] = len(final_evidence)

            # Phase 10: Confidence Engine
            start = time.time()
            confidence_result = ConfidenceEngine.calculate_confidence(final_evidence)
            metrics["confidence_ms"] = int((time.time() - start) * 1000)
            metrics["confidence_level"] = confidence_result["level"]

            metrics["total_duration_ms"] = int((time.time() - total_start) * 1000)

            logger.info(
                "Retrieval Pipeline Completed",
                extra={
                    "structured_log": True, 
                    "trace_id": trace_id, 
                    "stage": "Orchestrator",
                    "metrics": metrics
                }
            )

            return RetrievalResult(
                trace_id=trace_id,
                original_query=raw_query,
                normalized_query=normalized_query,
                rewritten_query=rewritten_query,
                intent=intent,
                strategy=strategy,
                evidence=final_evidence,
                confidence=confidence_result["level"],
                confidence_score=confidence_result["score"],
                metrics=metrics
            )

        except Exception as e:
            logger.error(
                f"Retrieval Pipeline Failed: {e}",
                extra={"structured_log": True, "trace_id": trace_id, "stage": "Orchestrator"},
                exc_info=True
            )
            raise
