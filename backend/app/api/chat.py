"""Chat API endpoint router.

Defines client interface entry points for query processing and diagnostics.
"""

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.core.settings import settings
from app.pipeline.pipeline import PIPELINE
from app.pipeline.process import process_query

router = APIRouter()


class ChatRequest(BaseModel):
    """Pydantic schema validating chat API payload."""

    query: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., alias="sessionId", min_length=8, max_length=64)
    similarity_threshold: float | None = Field(None, alias="similarityThreshold", ge=0.0, le=1.0)
    stream: bool = False

    model_config = {"populate_by_name": True}

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Assert session ID format rules."""
        if not re.match(r"^[a-zA-Z0-9\-_]+$", v):
            raise ValueError(
                "sessionId must contain only alphanumeric characters, dashes, or underscores"
            )
        return v


@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest) -> dict[str, Any]:
    """Execute stateless pipeline query routing.

    Args:
        request: FastAPI Request context.
        body: Validated ChatRequest body parameters.

    Returns:
        JSON response mapped from final ConversationContext.
    """
    # Extract request ID from middleware context
    request_id = getattr(request.state, "request_id", "-")

    metadata = {}
    if body.similarity_threshold is not None:
        metadata["similarity_threshold"] = body.similarity_threshold

    import asyncio
    import inspect
    from fastapi.responses import StreamingResponse
    import json

    metadata["stream"] = body.stream
    stream_queue = asyncio.Queue() if body.stream else None
    if stream_queue:
        metadata["stream_queue"] = stream_queue

    if body.stream:
        async def event_generator():
            loop = asyncio.get_running_loop()
            
            # Run the process_query synchronously in a thread
            task = loop.run_in_executor(
                None,
                process_query,
                body.query, body.session_id, request_id, metadata if metadata else None
            )

            # While task is running, check the queue for progress events
            while not task.done():
                try:
                    event = await asyncio.wait_for(stream_queue.get(), timeout=0.1)
                    yield f"data: {json.dumps({'status': event})}\n\n"
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    break

            try:
                response_payload = await asyncio.wait_for(task, timeout=12.0)
            except asyncio.TimeoutError:
                err_msg = "The request took too long to process. I couldn't find enough information in the uploaded documents."
                yield f"data: {json.dumps({'error': err_msg})}\n\n"
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

            if not response_payload.get("success", False):
                yield f"data: {json.dumps({'error': response_payload})}\n\n"
                return

            if inspect.isasyncgen(response_payload.get("answer")):
                generator = response_payload.pop("answer")
                try:
                    # Enforce the remainder of the 12s budget for the stream
                    async def bounded_generator():
                        start_stream = time.perf_counter()
                        async for chunk in generator:
                            if time.perf_counter() - start_stream > 12.0:
                                break
                            yield chunk
                    
                    async for chunk in bounded_generator():
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

                response_payload["answer"] = ""
                yield f"data: {json.dumps({'final': response_payload})}\n\n"
                yield "data: [DONE]\n\n"
            else:
                yield f"data: {json.dumps({'final': response_payload})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Non-streaming fallback
        try:
            task = asyncio.to_thread(
                process_query,
                original_query=body.query,
                session_id=body.session_id,
                request_id=request_id,
                metadata=metadata if metadata else None,
            )
            response_payload = await asyncio.wait_for(task, timeout=12.0)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "intent": "FALLBACK",
                "answer": "The request took too long to process. I couldn't find enough information in the uploaded documents.",
                "reasonCode": "GLOBAL_TIMEOUT"
            }

        if not response_payload.get("success", False):
            raise HTTPException(status_code=400, detail=response_payload)

        if inspect.isasyncgen(response_payload.get("answer")):
            full_text = ""
            start_stream = time.perf_counter()
            try:
                async for chunk in response_payload["answer"]:
                    if time.perf_counter() - start_stream > 12.0:
                        break
                    full_text += chunk
            except asyncio.TimeoutError:
                pass
            response_payload["answer"] = full_text

        return response_payload


@router.get("/debug/pipeline")
async def debug_pipeline_endpoint() -> dict[str, Any]:
    """Diagnostics helper exposing explicit pipeline engine sequences.

    Returns:
        JSON trace payload listing names.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403, detail="Pipeline debugging is disabled in production."
        )

    engine_names = [engine.name for engine in PIPELINE]
    return {
        "debug": True,
        "engineOrder": engine_names,
        "totalEnginesCount": len(engine_names),
    }


@router.post("/debug/rag-trace")
async def debug_rag_trace_endpoint(request: Request, body: ChatRequest) -> dict[str, Any]:
    """Execute pipeline and return deep RAG trace for debugging and verification."""
    request_id = getattr(request.state, "request_id", "-")

    metadata = {}
    if body.similarity_threshold is not None:
        metadata["similarity_threshold"] = body.similarity_threshold

    import asyncio
    response_payload = await asyncio.to_thread(
        process_query,
        original_query=body.query,
        session_id=body.session_id,
        request_id=request_id,
        metadata=metadata if metadata else None,
    )

    if not response_payload.get("success", False):
        raise HTTPException(status_code=400, detail=response_payload)

    # Extract specific trace details requested in Phase 6 requirements
    trace = response_payload.get("trace", [])
    meta = response_payload.get("metadata", {})
    
    rag_metadata = {}
    for entry in trace:
        if entry.get("engine") == "RAGRetrieval":
            rag_metadata = entry
            break

    from app.utils.metrics import global_metrics
    
    # Extract provider metrics from the RAGEngine in the pipeline
    provider_metrics = []
    from app.pipeline.pipeline import PIPELINE
    for engine in PIPELINE:
        if engine.name == "RAGRetrieval":
            if hasattr(engine, "generator") and hasattr(engine.generator, "get_all_metrics"):
                provider_metrics = engine.generator.get_all_metrics()
            break
            
    # Session state
    from app.utils.session import SessionStore
    session_state = SessionStore.get_state(body.session_id)
    
    warmup_stats = getattr(request.app.state, "warmup_stats", {})
    
    return {
        "original_query": body.query,
        "normalized_query": response_payload.get("normalizedQuery"),
        "resolved_query": response_payload.get("resolvedQuery"),
        "expanded_query": meta.get("expanded_query", ""),  # Assuming we can get it
        "decision": meta.get("decision"),
        "embedding_time_ms": rag_metadata.get("embeddingTimeMs", 0),
        "search_time_ms": rag_metadata.get("searchTimeMs", 0),
        "llm_latency_ms": rag_metadata.get("llmLatencyMs", 0),
        "total_latency_ms": rag_metadata.get("totalLatencyMs", 0),
        "has_metadata_match": rag_metadata.get("has_metadata_match", False),
        "has_keyword_match": rag_metadata.get("has_keyword_match", False),
        "retrieval_planner": rag_metadata.get("retrieval_planner", {}),
        "response_plan": rag_metadata.get("response_plan", {}),
        "retrieved_chunks": rag_metadata.get("retrievedChunks", []),
        "chunk_count": rag_metadata.get("chunkCount", 0),
        "confidence_tier": rag_metadata.get("confidence_tier", ""),
        "highest_similarity": rag_metadata.get("highest_similarity", 0),
        "answer": response_payload.get("answer"),
        "full_trace": trace,
        "pipeline_snapshots": response_payload.get("trace", []),
        "enterprise_metrics": global_metrics.get_metrics(),
        "provider_metrics": provider_metrics,
        "warmup_stats": warmup_stats,
        "session_state": {
            "active_topic": session_state.active_topic,
            "active_document": session_state.active_document,
            "active_entities": session_state.active_entities,
            "is_compressed": session_state.is_compressed,
            "turn_count": len(session_state.history) // 2
        }
    }

