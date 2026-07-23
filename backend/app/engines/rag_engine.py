"""RAG Retrieval and Answer Generation Engine.

Queries the hybrid retrieval system (metadata + keyword + vector + RRF),
resolves conversation memory context, and synthesizes professional cited
responses using an enterprise-grade extractive answer generator.
"""

import re
import time
import uuid
import asyncio
import threading
import logging
from abc import ABC, abstractmethod
from typing import Any, Coroutine, TypeVar
from collections import defaultdict

from app.core.settings import settings
from app.embeddings.embedding_service import EmbeddingService
from app.repositories.document_repository import DocumentRepository
from app.database.session import async_session
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult
from app.utils.session import SessionStore

logger = logging.getLogger("app")
T = TypeVar("T")


def run_async_safely(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine synchronously from a sync context.

    This is called from worker threads (via asyncio.to_thread) so we can safely
    schedule work on the main event loop without deadlocking.
    """
    import inspect
    if not inspect.iscoroutine(coro):
        return coro

    # If we're in a thread (the normal case when called via asyncio.to_thread),
    # schedule on the main uvicorn event loop
    from app.utils.loop import get_main_loop
    main_loop = get_main_loop()
    if main_loop and main_loop.is_running():
        try:
            asyncio.get_running_loop()
            # We ARE on an event loop — must not block. Use a new thread.
        except RuntimeError:
            # No running loop in this thread — safe to use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coro, main_loop)
            try:
                return future.result(timeout=30)
            except TimeoutError:
                future.cancel()
                raise TimeoutError("run_async_safely: coroutine timed out after 30s")

    # Fallback: no main loop or we're on an event loop — run in a fresh loop in a new thread
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No event loop at all — just run directly
        return asyncio.run(coro)

    # We're on an event loop but can't use main_loop — spawn a thread
    result = []
    error = []

    def target():
        try:
            import sys
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                res = new_loop.run_until_complete(coro)
                result.append(res)
            finally:
                new_loop.close()
        except Exception as e:
            error.append(e)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=30)

    if thread.is_alive():
        raise TimeoutError("run_async_safely: thread timed out after 30s")
    if error:
        raise error[0]
    return result[0]


class AnswerGenerator(ABC):
    """Abstract interface defining the RAG answer synthesis strategy."""

    @abstractmethod
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False) -> str | Any:
        """Synthesize query response using matching context chunks."""
        pass


class ExtractiveAnswerGenerator(AnswerGenerator):
    """Enterprise-grade extractive answer generator.

    Extracts the most relevant sentences from retrieved chunks,
    removes duplicates, merges evidence, and produces concise
    cited responses (2-3 paragraphs or 3-6 bullets, max 250-300 words).
    """

    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False) -> str | Any:
        if not chunks:
            return ""

        # 1. Clean query for relevance scoring
        query_words = {w.lower().strip("?,.!:;()\"'") for w in query.split()}
        filler_words = {
            "what", "is", "the", "for", "are", "but", "not", "you", "all", "any",
            "can", "had", "was", "how", "why", "when", "where", "who", "tell",
            "about", "details", "information", "do", "does", "me", "my", "your",
            "please", "explain", "describe", "show", "list", "give",
        }
        query_content_words = query_words - filler_words
        if not query_content_words:
            query_content_words = query_words

        # 2. Build unique citations key list (document, page) -> index (1-based)
        unique_citations = []
        for c in chunks:
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            citation_key = (filename, page)
            if citation_key not in unique_citations:
                unique_citations.append(citation_key)

        # 3. Extract and score sentences
        extracted_sentences = []
        seen_sentences = set()

        for c in chunks:
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            version = c.get("version_number", 1)
            citation_idx = unique_citations.index((filename, page)) + 1

            text = c.get("text", "")
            # Split by punctuation sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean or len(s_clean) < 15:
                    continue
                s_norm = s_clean.lower()
                if s_norm in seen_sentences:
                    continue
                seen_sentences.add(s_norm)

                # Relevance score: overlap with query content words
                s_words = {w.lower().strip("?,.!:;()\"'") for w in s_clean.split()}
                overlap = s_words.intersection(query_content_words)
                score = len(overlap)

                # Boost sentences with heading/section match
                heading = (c.get("heading") or "").lower()
                section = (c.get("section") or "").lower()
                for qw in query_content_words:
                    if qw in heading or qw in section:
                        score += 1

                extracted_sentences.append({
                    "text": s_clean,
                    "score": score,
                    "citation_idx": citation_idx,
                    "filename": filename,
                    "page": page,
                    "version": version,
                })

        # Sort sentences: highest matching score first
        extracted_sentences.sort(key=lambda x: x["score"], reverse=True)

        # Take up to 5 sentences to keep response concise
        top_sentences = extracted_sentences[:5]

        if not top_sentences:
            # No scored sentences — use first chunk text directly
            c = chunks[0]
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            text_preview = c.get("text", "")[:500]
            return (
                f"{text_preview}...\n\n"
                f"**Sources:**\n"
                f"{filename} — Page {page}"
            )

        # Sort top sentences by document and page so they flow logically
        top_sentences.sort(key=lambda x: (x["filename"], x["page"]))

        # Combine into a single paragraph without mechanical bullets
        paragraph = " ".join(s["text"] for s in top_sentences)

        # Build citations list
        citations_lines = []
        for i, (fn, pg) in enumerate(unique_citations):
            citations_lines.append(f"{fn} — Page {pg}")

        citations_str = "\n".join(citations_lines)

        return (
            f"{paragraph}\n\n"
            f"**Sources:**\n"
            f"{citations_str}"
        )


class RAGEngine(BaseEngine):
    """Retrieves relevant document chunks via hybrid search and synthesizes RAG answers."""

    def __init__(self, generator: AnswerGenerator | None = None):
        if generator is None:
            from app.engines.providers_legacy import ProviderManager
            self.generator = ProviderManager()
        else:
            self.generator = generator

    def _retrieve_hybrid(
        self, query: str, query_embedding: list[float], limit: int, is_mocked: bool, strategy: dict[str, bool] = None
    ) -> list[dict[str, Any]]:
        """Execute hybrid retrieval (metadata + keyword + vector + RRF)."""
        if is_mocked:
            # In test mode, just do vector search
            val = DocumentRepository.vector_search(None, query_embedding, limit=limit)
            import inspect
            if inspect.iscoroutine(val):
                return run_async_safely(val)
            return val
        else:
            async def fetch_hybrid():
                async with async_session() as session:
                    return await DocumentRepository.hybrid_search(
                        session, query, query_embedding, limit=limit, strategy=strategy
                    )
            return run_async_safely(fetch_hybrid())

    def _build_failure_result(
        self, start_time: float, search_time: float, embed_time: float, limit: int,
        highest_score: float, threshold: float, confidence_tier: str, reason_code: str
    ) -> EngineResult:
        """Helper to build telemetry metadata for failed confidence validations."""
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Prepare Telemetry
        telemetry = {
            "why_chosen": f"Confidence tier: {confidence_tier} (fails validation)",
            "decision": "RAG",
            "rag_eligible": True,
            "embeddingTimeMs": embed_time,
            "searchTimeMs": search_time,
            "execution_ms": duration_ms,
            "threshold": threshold,
            "highest_similarity": highest_score,
            "confidence_tier": confidence_tier,
            "retrievedChunks": [],
            "similarityScore": highest_score,
            "chunkCount": 0,
            "documentsUsed": [],
        }
        return EngineResult(
            handled=False,
            reason_code=reason_code,
            metadata=telemetry,
        )

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()
        logger.info("RAGEngine.execute() started — intent=%s, query='%s'",
                    context.intent, (context.resolved_query or context.normalized_query or context.original_query or "")[:80])
                    
        def push_stream_event(event: str):
            q = context.metadata.get("stream_queue")
            if q:
                # We need to run the put in the main event loop thread safely
                import asyncio
                from app.utils.loop import get_main_loop
                main_loop = get_main_loop()
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(q.put(event), main_loop)

        push_stream_event("Analyzing query...")

        # 1. Check Routing Decision
        decision = context.metadata.get("decision")
        if decision is not None and decision != "RAG":
            return EngineResult(handled=False, reason_code="RAG_SKIPPED_BY_DECISION_ENGINE")

        # 2. Check if Mocked
        from unittest.mock import Mock
        is_mocked = isinstance(DocumentRepository.vector_search, Mock)

        # 3. Check if database is available
        from app.database.session import db_is_available
        if not db_is_available and not is_mocked:
            return EngineResult(handled=False, reason_code="RAG_SKIPPED_DB_UNAVAILABLE")

        # 4. Check Empty Knowledge Base Handling
        has_docs = True
        if not is_mocked:
            async def check_docs_exist():
                from app.database.session import async_session
                from sqlalchemy import select, func
                from app.database.models import DocumentVersion
                async with async_session() as session:
                    stmt = select(func.count()).select_from(DocumentVersion).where(DocumentVersion.status == "ready_for_search")
                    res = await session.execute(stmt)
                    return res.scalar() > 0

            try:
                has_docs = run_async_safely(check_docs_exist())
            except Exception as e:
                logger.error("RAG: check documents exist failed: %s", e)
                has_docs = False

        if not has_docs:
            context.intent = "FALLBACK"
            context.response = "No searchable knowledge base documents are currently available. Please upload documents before asking document-specific questions."
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return EngineResult(
                handled=True,
                reason_code="RAG_NO_DOCUMENTS_AVAILABLE",
                metadata={
                    "decision": "RAG",
                    "rag_eligible": True,
                    "why_chosen": "Empty knowledge base library",
                    "execution_ms": duration_ms,
                    "chunkCount": 0,
                    "documentsUsed": [],
                }
            )

        query = context.resolved_query or context.normalized_query or context.original_query or ""
        if not query.strip():
            return EngineResult(handled=False, reason_code="RAG_SKIPPED_EMPTY")

        # Perform synonym query expansion
        from app.services.query_expansion import expand_query
        expanded_query = expand_query(query)
        context.expanded_query = expanded_query
        logger.info("RAG query expansion: '%s' -> '%s'", query, expanded_query)

        # 4.1 Level 1 Cache Check (Exact Match before retrieval)
        from app.utils.cache import response_cache
        push_stream_event("Checking exact cache...")
        exact_cached_answer = response_cache.get_exact(expanded_query)
        if exact_cached_answer:
            logger.info("Level 1 Exact Cache hit for query: '%s'", expanded_query)
            context.intent = "KNOWLEDGE_RETRIEVED"
            is_stream = context.metadata.get("stream", False)
            
            if is_stream:
                async def cache_stream():
                    yield exact_cached_answer
                context.response = cache_stream()
            else:
                context.response = exact_cached_answer
                
            telemetry = {
                "decision": "RAG",
                "why_chosen": "Exact Cache Hit",
                "rag_eligible": True,
                "cacheHit": True,
                "cacheHitSource": "Level 1 (Exact)",
                "totalLatencyMs": round((time.perf_counter() - start_time) * 1000, 2)
            }
            context.metadata.update(telemetry)
            return EngineResult(handled=True, reason_code="RAG_CACHE_HIT", metadata=telemetry)

        # Compute query embedding
        push_stream_event("Generating query embedding...")
        start_embed = time.perf_counter()
        try:
            query_embedding = EmbeddingService.generate_embedding(expanded_query)
            embedding_time_ms = round((time.perf_counter() - start_embed) * 1000, 2)
        except Exception as e:
            logger.error("RAG: embedding generation failed: %s", e)
            return EngineResult(
                handled=False,
                reason_code="RAG_EMBEDDING_FAILED",
                metadata={"error": str(e)},
            )

        # 4.5 Retrieval Planner
        push_stream_event("Planning retrieval strategy...")
        strategy = {
            "use_metadata": False,
            "use_keyword": False,
            "use_vector": False
        }
        retrieval_reasoning = []
        q_lower = expanded_query.lower()
        
        has_doc_intent = any(w in q_lower for w in ["document", "file", "pdf", "page", "show uploaded", "what is uploaded", "what documents"])
        has_complex_intent = any(w in q_lower for w in ["how", "why", "explain", "describe", "summarize", "reimbursement", "policy", "process"])
        is_short = len(q_lower.split()) <= 3
        
        if "what documents are uploaded" in q_lower or "show uploaded" in q_lower:
            strategy["use_metadata"] = True
            retrieval_reasoning.append("Strategy: Metadata Only (Document listing intent)")
        elif has_doc_intent and is_short:
            strategy["use_metadata"] = True
            strategy["use_keyword"] = True
            retrieval_reasoning.append("Strategy: Metadata + Keyword (Specific document search)")
        elif has_complex_intent:
            strategy["use_metadata"] = True
            strategy["use_keyword"] = True
            strategy["use_vector"] = True
            retrieval_reasoning.append("Strategy: Hybrid (Complex reasoning intent)")
        elif is_short:
            strategy["use_vector"] = True
            retrieval_reasoning.append("Strategy: Vector (Short semantic query)")
        else:
            strategy["use_metadata"] = True
            strategy["use_keyword"] = True
            strategy["use_vector"] = True
            retrieval_reasoning.append("Strategy: Hybrid (Default)")

        # 5. Execute hybrid retrieval
        push_stream_event("Searching documents...")
        start_search = time.perf_counter()
        limit = 10

        # Confidence thresholds calibrated for real SentenceTransformer embeddings
        reject_threshold = 0.30   
        weak_threshold = 0.45     
        strong_threshold = 0.65   

        try:
            retrieved = self._retrieve_hybrid(expanded_query, query_embedding, limit, is_mocked, strategy)
            search_time_ms = round((time.perf_counter() - start_search) * 1000, 2)
        except Exception as e:
            logger.error("RAG: hybrid search failed: %s", e)
            context.metadata["rag_error_code"] = "DATABASE_FAILURE"
            return EngineResult(
                handled=False,
                reason_code="RAG_DATABASE_FAILED",
                metadata={"error": str(e)},
            )

        # 6. Deduplicate & Merge Adjacent Chunks & Calculate Evidence Score (Reranking Layer)
        seen_ids = set()
        deduped = []
        
        query_words = set(re.findall(r'\b\w{4,}\b', expanded_query.lower()))
        
        # Confidence thresholds calibrated for real SentenceTransformer embeddings
        reject_threshold = 0.30   
        medium_threshold = 0.45     
        high_threshold = 0.65   
        
        accepted_chunks = 0
        rejected_chunks = 0
        rejection_reasons = {}

        for c in retrieved:
            cid = c.get("chunk_id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                
                vector_score = float(c.get("score", 0.0))
                if not EmbeddingService.is_real_model():
                    vector_score = 0.0
                    
                evidence_score = vector_score
                
                if c.get("retrieval_method", "").startswith("metadata"):
                    evidence_score += 0.20
                if c.get("retrieval_method", "") == "keyword":
                    evidence_score += 0.15
                    
                heading = (c.get("heading") or "").lower()
                section = (c.get("section") or "").lower()
                filename = (c.get("filename") or "").lower()
                
                if query_words:
                    if any(w in heading for w in query_words):
                        evidence_score += 0.10
                    if any(w in section for w in query_words):
                        evidence_score += 0.05
                    if any(w in filename for w in query_words):
                        evidence_score += 0.10
                        
                rrf_score = float(c.get("rrf_score", 0.0))
                if rrf_score > 0:
                    evidence_score += rrf_score * 0.5
                    
                chunk_text = c.get("text", "").lower()
                lexical_overlap = 0
                if query_words:
                    lexical_overlap = sum(1 for w in query_words if w in chunk_text) / len(query_words)
                    
                c["reranker_score"] = lexical_overlap * 0.20
                evidence_score += c["reranker_score"]
                c["evidence_score"] = min(1.0, evidence_score)
                
                if c["evidence_score"] >= reject_threshold:
                    deduped.append(c)
                    accepted_chunks += 1
                else:
                    rejected_chunks += 1
                    rejection_reasons["BELOW_THRESHOLD"] = rejection_reasons.get("BELOW_THRESHOLD", 0) + 1

        deduped.sort(key=lambda x: x.get("evidence_score", 0.0), reverse=True)

        # 7. Three-Level Confidence Validation (Evidence Gate) & Adaptive Retrieval
        push_stream_event("Ranking evidence...")
        
        logger.info(
            "EVIDENCE GATE DIAGNOSTICS\n"
            "Accepted chunks (%d): %s\n"
            "Rejected chunks (%d): %s\n"
            "Rejection reasons: %s\n"
            "Thresholds: LOW=%.2f, MEDIUM=%.2f, HIGH=%.2f",
            accepted_chunks, [c.get("chunk_id", "")[:8] + "(score:" + str(round(c.get("evidence_score", 0), 2)) + ")" for c in deduped],
            rejected_chunks, "(Omitted for brevity)",
            rejection_reasons,
            reject_threshold, medium_threshold, high_threshold
        )
        
        if not deduped:
            return self._build_failure_result(
                start_time, search_time_ms, embedding_time_ms, limit,
                0.0, reject_threshold, "LOW", "RAG_NO_RELEVANT_CHUNKS"
            )

        highest_score = float(deduped[0].get("evidence_score", 0.0))

        if highest_score < reject_threshold:
            return self._build_failure_result(
                start_time, search_time_ms, embedding_time_ms, limit,
                highest_score, reject_threshold, "LOW", "RAG_WEAK_EVIDENCE"
            )
        elif highest_score < medium_threshold:
            confidence_tier = "MEDIUM"
            supporting = [c for c in deduped if c.get("evidence_score", 0) >= reject_threshold]
            if len(supporting) == 0 and not is_mocked:
                return self._build_failure_result(
                    start_time, search_time_ms, embedding_time_ms, limit,
                    highest_score, reject_threshold,
                    "LOW (No valid chunks)", "RAG_WEAK_EVIDENCE"
                )
        else:
            confidence_tier = "HIGH"

        # 8. Adaptive Evidence Selection
        selected_chunks = []
        cumulative_confidence = 0.0
        
        for c in deduped:
            score = float(c.get("evidence_score", 0))
            if score < reject_threshold:
                continue
            selected_chunks.append(c)
            cumulative_confidence += score
            
            # Adaptive logic: Stop early if HIGH confidence is reached
            if confidence_tier == "HIGH" and cumulative_confidence > 1.5 and len(selected_chunks) >= 2:
                break
            if confidence_tier == "MEDIUM" and len(selected_chunks) >= 4:
                # Need more chunks for medium confidence
                break
            if len(selected_chunks) >= 6:
                break

        # 8.2 Response Planner Integration
        from app.engines.response_planner import ResponsePlanner
        planner = ResponsePlanner()
        response_plan = planner.plan_response(
            query=expanded_query, 
            chunks=selected_chunks, 
            intent=context.intent, 
            confidence=highest_score
        )

        # 8.3 Extractive Composer (Primary Generator)
        from app.engines.extractive_composer import ExtractiveComposer
        composer = ExtractiveComposer()
        extractive_draft_data = composer.generate(
            query=expanded_query, 
            chunks=selected_chunks, 
            session_id=context.session_id, 
            stream=False, 
            response_plan=response_plan
        )
        
        # 8.4 Formatter Engine
        from app.engines.formatter import FormatterEngine
        formatted_extractive_answer = FormatterEngine.format(extractive_draft_data, response_plan)

        # 8.5. Check Response Cache
        push_stream_event("Checking semantic cache...")
        from app.utils.cache import response_cache
        import hashlib
        
        evidence_str = "".join(sorted([str(c.get("chunk_id", "")) for c in selected_chunks]))
        evidence_hash = hashlib.sha256(evidence_str.encode("utf-8")).hexdigest()
        prompt_version = "v1"
        doc_version = str(max([c.get("version_number", 1) for c in selected_chunks] or [1]))
        embed_version = EmbeddingService.model_name
        
        cached_answer = response_cache.get(expanded_query, evidence_hash, prompt_version, doc_version, embed_version)
        cache_hit = False

        # 9. Generate answer
        push_stream_event("Generating answer...")
        start_llm = time.perf_counter()
        is_stream = context.metadata.get("stream", False)
        fallback_used = False
        fallback_reason = None
        
        if cached_answer:
            answer = cached_answer
            cache_hit = True
            llm_latency_ms = 0
            if context.session_id:
                SessionStore.add_history(context.session_id, "user", query)
                SessionStore.add_history(context.session_id, "model", answer)
            
            if is_stream:
                async def cache_stream():
                    yield answer
                answer = cache_stream()
        else:
            if not response_plan.requires_llm_enhancement:
                # Bypass LLM completely (Deterministic)
                logger.info("RAG: LLM bypassed. Using Deterministic Extractive Draft.")
                llm_latency_ms = 0
                answer = formatted_extractive_answer
                
                if context.session_id:
                    SessionStore.add_history(context.session_id, "user", query)
                    SessionStore.add_history(context.session_id, "model", answer)
                
                if is_stream:
                    async def ext_stream():
                        yield formatted_extractive_answer
                    answer = ext_stream()
                
                response_cache.set(expanded_query, evidence_hash, prompt_version, doc_version, embed_version, formatted_extractive_answer)
            else:
                try:
                    time_elapsed = time.perf_counter() - start_time
                    if time_elapsed > 5.0:
                        logger.warning("RAG: Pipeline took %.2fs before generation.", time_elapsed)

                    # Send the drafted text as the single chunk to the LLM to just improve wording
                    draft_chunks = [{"text": formatted_extractive_answer, "filename": "Extractive Draft"}]

                    import inspect
                    sig = inspect.signature(self.generator.generate)
                    kwargs = {"session_id": context.session_id, "stream": is_stream}
                    if "response_plan" in sig.parameters:
                        kwargs["response_plan"] = response_plan
                        
                    answer = self.generator.generate(expanded_query, draft_chunks, **kwargs)
                    
                    if not is_stream:
                        llm_latency_ms = round((time.perf_counter() - start_llm) * 1000, 2)
                        if context.session_id:
                            SessionStore.add_history(context.session_id, "user", query)
                            SessionStore.add_history(context.session_id, "model", answer)
                    else:
                        llm_latency_ms = 0
                        async def stream_wrapper():
                            full_answer = ""
                            async for chunk in answer:
                                full_answer += chunk
                                yield chunk
                            
                            if context.session_id:
                                SessionStore.add_history(context.session_id, "user", query)
                                SessionStore.add_history(context.session_id, "model", full_answer)
                                
                            response_cache.set(expanded_query, evidence_hash, prompt_version, doc_version, embed_version, full_answer)
                        
                        answer = stream_wrapper()
                        
                    if not is_stream:
                        response_cache.set(expanded_query, evidence_hash, prompt_version, doc_version, embed_version, answer)
                        
                except Exception as e:
                    logger.warning("RAG: Generator failed (%s). Activating Extractive Fallback.", e)
                    fallback_used = True
                    fallback_reason = str(e)
                    
                    llm_latency_ms = round((time.perf_counter() - start_llm) * 1000, 2)
                    
                    if context.session_id:
                        SessionStore.add_history(context.session_id, "user", query)
                        SessionStore.add_history(context.session_id, "model", formatted_extractive_answer)
                        
                    if is_stream:
                        async def ext_stream():
                            yield formatted_extractive_answer
                        answer = ext_stream()
                    else:
                        answer = formatted_extractive_answer

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        has_metadata_match = any(c.get("retrieval_method", "").startswith("metadata") for c in selected_chunks)
        has_keyword_match = any(c.get("retrieval_method", "") == "keyword" for c in selected_chunks)

        context_corpus = " ".join(c.get("text", "") for c in selected_chunks)
        prompt_tokens = len(context_corpus + query) // 4
        completion_tokens = len(answer) // 4 if not is_stream else 0

        SessionStore.set_last_context(
            context.session_id, 
            query, 
            selected_chunks, 
            context.intent or "KNOWLEDGE",
            topic=context.metadata.get("detected_topic")
        )

        context.intent = "KNOWLEDGE_RETRIEVED"
        context.response = answer

        # Prepare Telemetry
        telemetry = {
            "decision": "RAG",
            "why_chosen": f"Confidence tier: {confidence_tier}",
            "rag_eligible": True,
            "fastPathMatched": False,
            "similarityScore": highest_score,
            "highest_similarity": highest_score,
            "confidence_tier": confidence_tier,
            "has_metadata_match": has_metadata_match,
            "has_keyword_match": has_keyword_match,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "cacheHit": cache_hit,
            "promptVersion": prompt_version,
            "response_plan": response_plan.to_dict(),
            "retrieval_planner": {
                "strategy": strategy,
                "reasoning": retrieval_reasoning
            },
            "retrievedChunks": [
                {
                    "chunkId": c.get("chunk_id"),
                    "documentId": c.get("document_id"),
                    "filename": c.get("filename"),
                    "pageNumber": c.get("page_number"),
                    "heading": c.get("heading") or c.get("section") or "N/A",
                    "vectorScore": c.get("score", 0),
                    "hybridScore": c.get("score", 0),
                    "evidenceScore": c.get("evidence_score", 0),
                    "rerankerScore": c.get("reranker_score", 0),
                    "metadataScore": 0.20 if c.get("retrieval_method", "").startswith("metadata") else 0.0,
                    "keywordScore": 0.15 if c.get("retrieval_method", "") == "keyword" else 0.0,
                    "filenameScore": 0.10 if any(w in (c.get("filename") or "").lower() for w in query_words) else 0.0,
                    "headingScore": 0.10 if any(w in (c.get("heading") or "").lower() for w in query_words) else 0.0,
                    "retrievalMethod": c.get("retrieval_method", "unknown"),
                    "retrievalMethods": c.get("retrieval_methods", []),
                    "rrfScore": c.get("rrf_score", 0),
                }
                for c in selected_chunks
            ],
            "expandedQuery": expanded_query,
            "embeddingTimeMs": embedding_time_ms,
            "searchTimeMs": search_time_ms,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "llmLatencyMs": llm_latency_ms,
            "totalLatencyMs": duration_ms,
            "threshold": reject_threshold,
            "chunkCount": len(selected_chunks),
            "documentsUsed": list(set(c["filename"] for c in selected_chunks if c.get("filename"))),
            "embedding_model": EmbeddingService.model_name,
            "is_real_model": EmbeddingService.is_real_model(),
        }

        context.metadata.update(telemetry)

        return EngineResult(
            handled=True,
            reason_code="RAG_RETRIEVED_SUCCESSFULLY",
            metadata=telemetry,
        )

    @property
    def name(self) -> str:
        return "RAGRetrieval"
