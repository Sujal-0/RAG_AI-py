"""Retrieval Orchestrator.

The exclusive public entry point for the Retrieval Engine. 
Coordinates the 10-stage pipeline, managing dependencies, correlation IDs, 
structured logging, and timing metrics across all execution phases.
"""

import logging
import time
import uuid
import asyncio
import re
from typing import Any, Optional
from rapidfuzz import fuzz
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

class MockChunk:
    def __init__(self, text: str, document_id: str = "static_fastpath"):
        self.text = text
        self.chunk_metadata = {"document_id": document_id}
        self.chunk_index = 0
        self.id = document_id
        self.token_count = len(text.split())

from app.core.settings import settings
from app.engines.query.query_analyzer import QueryAnalyzer, NormalizedQuery
from app.engines.query.intent_detector import IntentDetectionEngine
from app.engines.query.conversation_resolver import ConversationResolver
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
    debug_info: dict[str, Any] = None
    plan: Any = None


class RetrievalOrchestrator:
    """Coordinates the end-to-end retrieval process."""

    @classmethod
    async def execute(
        cls, 
        session: AsyncSession, 
        raw_query: str, 
        session_history: list[dict[str, str]],
        plan: Any = None
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

            # --- Tier-1 Semantic Gatekeeper ---
            import re
            from app.conversation.planner.gibberish_detector import EnterpriseGibberishDetector
            from app.retrievers.static_knowledge import ROUTING_KEYS
            
            fast_query = raw_query.strip().lower()

            if re.fullmatch(r'^(hi|hello|hey|good morning|good afternoon|good evening|greetings)[\s\W]*$', fast_query):
                metrics["total_duration_ms"] = int((time.time() - total_start) * 1000)
                logger.info("Tier-1 Gatekeeper: Greeting Intercepted", extra={"structured_log": True, "trace_id": trace_id})
                return RetrievalResult(
                    trace_id=trace_id,
                    original_query=raw_query,
                    normalized_query=normalized_query,
                    rewritten_query=raw_query,
                    intent="FASTPATH_GREETING",
                    strategy=None,
                    evidence=[{
                        "chunk": MockChunk("Hello! I am the Mobiloitte AI Platform Assistant. How can I help you today?", "greeting_gate")
                    }],
                    confidence="High",
                    confidence_score=1.0,
                    metrics=metrics,
                    debug_info={"intercepted": "greeting"},
                    plan=plan
                )
                
            if EnterpriseGibberishDetector.is_gibberish(raw_query):
                metrics["total_duration_ms"] = int((time.time() - total_start) * 1000)
                logger.info("Tier-1 Gatekeeper: Gibberish Intercepted", extra={"structured_log": True, "trace_id": trace_id})
                return RetrievalResult(
                    trace_id=trace_id,
                    original_query=raw_query,
                    normalized_query=normalized_query,
                    rewritten_query=raw_query,
                    intent="FASTPATH_GIBBERISH",
                    strategy=None,
                    evidence=[{
                        "chunk": MockChunk("I didn't quite understand that. Could you please rephrase your question?", "gibberish_gate")
                    }],
                    confidence="High",
                    confidence_score=1.0,
                    metrics=metrics,
                    debug_info={"intercepted": "gibberish"},
                    plan=plan
                )



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

            # Detect Intent (Use override from Planner if available - ONE source of truth)
            start = time.time()
            if plan and hasattr(plan, "intent"):
                intent = plan.intent
                max_chunks_limit = getattr(plan, "max_chunks", 3)
                processed_query = getattr(plan, "processed_query", raw_query)
            else:
                from app.conversation.planner.decision_engine import DecisionEngine
                decision = DecisionEngine.classify(normalized_query.normalized_text)
                intent = decision["intent"]
                max_chunks_limit = 3
                processed_query = decision.get("processed_query", normalized_query.normalized_text)
            metrics["intent_detection_ms"] = int((time.time() - start) * 1000)

            # --- Phase 1b: Response Planner (Retrieval Optimization) ---
            # Fast Path: Greeting, Thanks, etc. should not reach here due to orchestrator bypass
            if plan and getattr(plan, "fastpath", False):
                metrics["total_duration_ms"] = int((time.time() - total_start) * 1000)
                metrics["retrieved_chunks"] = 0
                metrics["returned_chunks"] = 0
                return RetrievalResult(
                    trace_id=trace_id,
                    original_query=raw_query,
                    normalized_query=normalized_query,
                    rewritten_query=processed_query,
                    intent=intent,
                    strategy=RetrievalStrategyEngine.determine_strategy(intent, normalized_query.response_expectation),
                    evidence=[],
                    confidence="High",
                    confidence_score=1.0,
                    metrics=metrics,
                    debug_info={},
                    plan=plan
                )

            # Dynamic Top K based on intent
            dynamic_top_k = max(max_chunks_limit * 3, 10)

            # Phase 2: Conversation Resolution & Rewrite
            start = time.time()
            
            # Smart Context Gateway (Bypass Query Rewrite)
            bridge_words = {"he", "she", "it", "they", "this", "that", "compare", "more", "detail", "summarize"}
            words = set(re.findall(r'\b\w+\b', processed_query.lower()))
            
            if session_history and len(session_history) > 0 and words.intersection(bridge_words):
                rewritten_query = await ConversationResolver.resolve_state(
                    processed_query, session_history, active_entities
                )
            else:
                rewritten_query = processed_query
                
            metrics["conversation_ms"] = int((time.time() - start) * 1000)

            # Phase 3: Strategy Engine
            strategy = RetrievalStrategyEngine.determine_strategy(
                intent, normalized_query.response_expectation
            )

            # Phase 4: Metadata Filtering
            filters = MetadataFilterEngine.generate_filters(
                strategy, normalized_query, active_entities
            )

            # Phase 5: Fast-Fetch Execution (HNSW + Cross-Encoder)
            start = time.time()
            
            # Local Multi-Query Vector Deconstruction
            query_str = rewritten_query.lower()
            split_queries = []
            conjunctions = [" as well as ", " along with ", " and ", " or "]
            
            for conj in conjunctions:
                if conj in query_str:
                    parts = query_str.split(conj)
                    for p in parts:
                        p_strip = p.strip()
                        # If a sub-query string is fewer than 3 words, fallback to original rewritten_query to prevent keyword truncation
                        if len(p_strip.split()) < 3:
                            split_queries.append(rewritten_query)
                        else:
                            split_queries.append(p_strip)
                    break
                    
            if not split_queries:
                split_queries = [rewritten_query]
                
            final_evidence = []
            seen_chunks = set()
            
            for sub_query in split_queries:
                sub_evidence = await HybridRetriever.retrieve(
                    session,
                    original_query=normalized_query,
                    rewritten_query=sub_query,
                    strategy=strategy,
                    metadata_filters=filters,
                    top_k=dynamic_top_k
                )
                for item in sub_evidence:
                    chunk_obj = item.get("chunk") if isinstance(item, dict) else getattr(item, "chunk", None)
                    chunk_text = chunk_obj.get("text") if isinstance(chunk_obj, dict) else getattr(chunk_obj, "text", str(chunk_obj))
                    
                    if chunk_text and chunk_text not in seen_chunks:
                        seen_chunks.add(chunk_text)
                        
                        # Rebuild as a strict standard dict layout matching cross-encoder target expectations
                        standard_item = {
                            "chunk": MockChunk(chunk_text),
                            "score": item.get("score", 0.0) if isinstance(item, dict) else getattr(item, "score", 0.0)
                        }
                        final_evidence.append(standard_item)
            
            # --- Vector Database Keyword Fallback ---
            if len(final_evidence) == 0:
                # Define conversational stop-words to ignore during database lookups
                STOP_WORDS = {"want", "know", "about", "tell", "show", "give", "find", "here", "with", "please", "query", "i", "to", "the"}
                
                # Strip punctuation and filter words
                cleaned_query = re.sub(r'[^\w\s]', '', rewritten_query.lower())
                keywords = [w for w in cleaned_query.split() if len(w) > 3 and w not in STOP_WORDS]
                
                if not keywords:
                    keywords = [rewritten_query.split()[-1]] if rewritten_query.split() else ["company"]
                    
                if keywords:
                    # Force rigid intersecting match (AND logic) to ensure high accuracy instead of broad OR fetching
                    fallback_search_term = " AND ".join(keywords[:3])
                    logger.info(f"Executing broad keyword fallback: {fallback_search_term}")
                    
                    fallback_evidence = await HybridRetriever.retrieve(
                        session,
                        original_query=normalized_query,
                        rewritten_query=fallback_search_term,
                        strategy=strategy,
                        metadata_filters=filters,
                        top_k=dynamic_top_k
                    )
                    
                    for item in fallback_evidence:
                        chunk_obj = item.get("chunk") if isinstance(item, dict) else getattr(item, "chunk", None)
                        chunk_text = chunk_obj.get("text") if isinstance(chunk_obj, dict) else getattr(chunk_obj, "text", str(chunk_obj))
                        
                        if chunk_text and chunk_text not in seen_chunks:
                            seen_chunks.add(chunk_text)
                            
                            standard_item = {
                                "chunk": MockChunk(chunk_text),
                                "score": item.get("score", 0.0) if isinstance(item, dict) else getattr(item, "score", 0.0)
                            }
                            final_evidence.append(standard_item)

            # --- Fallback Matching against EXPANDED Query ---
            if len(final_evidence) == 0:
                from app.retrievers import static_knowledge
                expanded_lower = rewritten_query.lower()
                best_match_text = None
                highest_score = 0
                
                # Dynamically evaluate the contextually expanded query against all static registry dimensions
                for key, content_text in static_knowledge.company_basics.items():
                    # Calculate mathematical contextual relevance across intent keys and fact arrays
                    key_score = fuzz.partial_ratio(expanded_lower, key.lower())
                    content_score = fuzz.token_set_ratio(expanded_lower, content_text.lower())
                    
                    max_score = max(key_score, content_score)
                    
                    # Anchor against a strict 70% enterprise confidence threshold
                    if max_score > 70 and max_score > highest_score:
                        highest_score = max_score
                        best_match_text = content_text
                        
                if best_match_text:
                    logger.info(f"Dynamic Static Fallback Triggered. Key Match Score: {highest_score}%")
                    
                    # Package the dynamic match safely as a structured piece of evidence for the generator
                    is_exact_static = True if highest_score > 85 else False
                    final_evidence.append({"chunk": {"text": best_match_text, "is_exact_static": is_exact_static}})
            
            metrics["retrieval_execution_ms"] = int((time.time() - start) * 1000)
            metrics["final_evidence_count"] = len(final_evidence)
            metrics["returned_chunks"] = len(final_evidence)

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

            debug_info = {
                "active_entities": active_entities,
                "strategy": strategy.strategy_name,
                "filters_applied": filters,
                "raw_retrieved_count": len(final_evidence) if final_evidence else 0
            }
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
                metrics=metrics,
                debug_info=debug_info,
                plan=plan
            )

        except Exception as e:
            logger.error(
                f"Retrieval Pipeline Failed: {e}",
                extra={"structured_log": True, "trace_id": trace_id, "stage": "Orchestrator"},
                exc_info=True
            )
            raise
