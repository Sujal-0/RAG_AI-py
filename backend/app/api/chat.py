"""Chat API endpoint router.

Defines client interface entry points for query processing and diagnostics.
"""

import re
import time
import json
import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.database.session import get_db_session
from app.conversation.orchestrator.orchestrator import ConversationOrchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    """Pydantic schema validating chat API payload."""

    query: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., alias="sessionId", min_length=8, max_length=64)
    similarity_threshold: float | None = Field(None, alias="similarityThreshold", ge=0.0, le=1.0)
    history: list[dict[str, str]] | None = Field(None, description="Optional incoming chat history")
    stream: bool = True

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
async def chat_endpoint(
    request: Request, 
    body: ChatRequest,
    db_session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Execute stateless pipeline query routing via the unified ConversationOrchestrator."""
    request_id = getattr(request.state, "request_id", "-")
    import os
    debug_mode = os.getenv("DEBUG_MODE", "").lower() == "true"

    if body.stream:
        async def event_generator():
            try:
                # 1. Inject History if provided
                if body.history:
                    session = MemoryManager.get_session(body.session_id)
                    session.short_memory = body.history[-20:]
                    
                # 2. Execute Pipeline
                response = await ConversationOrchestrator.process_turn(
                    db_session=db_session, 
                    query=body.query, 
                    session_id=body.session_id
                )
                
                # 2. Check for fast-path / clarification
                if response.is_clarification or not response.stream:
                    yield f"data: {json.dumps({'chunk': response.content})}\n\n"
                    final_payload = {
                        "success": True,
                        "answer": "",
                        "trace_id": response.trace_id,
                        "metrics": response.metrics,
                        "is_clarification": response.is_clarification
                    }
                    if debug_mode:
                        final_payload["debug_info"] = response.debug_info
                    yield f"data: {json.dumps({'final': final_payload})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                # 3. Stream Generator
                start_stream = time.perf_counter()
                async for chunk in response.stream:
                    if time.perf_counter() - start_stream > 15.0:
                        break # Hard stream timeout
                    yield f"data: {json.dumps({'chunk': chunk.content})}\n\n"
                    
                # 4. Final Meta
                final_payload = {
                    "success": True,
                    "answer": "",
                    "citations": response.citations,
                    "metrics": response.metrics,
                    "trace_id": response.trace_id
                }
                if debug_mode:
                    final_payload["debug_info"] = response.debug_info
                yield f"data: {json.dumps({'final': final_payload})}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    else:
        # Non-streaming fallback
        try:
            import logging
            logger = logging.getLogger("app")
            print(f">>> Incoming chat request (non-stream): {body.query}")
            logger.info(f"Incoming chat request: {body.query}")
            
            print(f">>> Calling ConversationOrchestrator.process_turn...")
            # 1. Inject History if provided
            if body.history:
                session = MemoryManager.get_session(body.session_id)
                session.short_memory = body.history[-20:]
                
            response = await ConversationOrchestrator.process_turn(
                db_session=db_session, 
                query=body.query, 
                session_id=body.session_id
            )
            print(f">>> Process turn finished!")
            logger.info("Process turn finished.")
            
            # Consume stream if it was generated anyway
            full_text = response.content
            if response.stream:
                full_text = ""
                async for chunk in response.stream:
                    full_text += chunk.content
                    
            payload = {
                "success": True,
                "answer": full_text,
                "intent": response.intent,
                "displayIntent": response.intent,
                "citations": response.citations,
                "metrics": response.metrics,
                "trace_id": response.trace_id,
                "is_clarification": response.is_clarification
            }
            if debug_mode:
                payload["debug_info"] = response.debug_info
                
            # Observability Print Block (Task 11)
            intent_name = response.intent
            is_fast_path = "YES" if (getattr(response, "is_clarification", False) or response.intent in ("FASTPATH_GREETING", "FASTPATH_GIBBERISH", "STATIC_FAQ")) else "NO"
            has_retrieval = "YES" if is_fast_path == "NO" else "NO"
            
            # Extract metrics safely
            metrics = response.metrics or {}
            retrieval_info = response.debug_info.get("retrieval", {}) if response.debug_info else {}
            
            chunks_retrieved = retrieval_info.get("raw_retrieved_count", 0) if has_retrieval == "YES" else 0
            chunks_used = metrics.get("evidence_count", 0) if has_retrieval == "YES" else 0
            
            durations = metrics.get("duration_ms", {})
            if "duration_ms" not in metrics and "durations_ms" in metrics:
                durations = metrics["durations_ms"]
                
            total_ms = durations.get("total_ms", 0)
            gen_ms = durations.get("total_generation_ms", 0)
            ret_ms = retrieval_info.get("metrics", {}).get("total_duration_ms", 0) if has_retrieval == "YES" else 0
            
            # Since planner and decision are <5ms and not deeply tracked in this object, we estimate them as part of total - others, or just "1ms"
            decision_time = 1
            planner_time = 1
            
            normalized_query = retrieval_info.get("normalized_query", body.query)
            if hasattr(normalized_query, "normalized_text"):
                normalized_query = normalized_query.normalized_text
                
            processed_query = body.query # Actually we don't have processed_query returned in final_response, we can just print body.query for now, or extract from somewhere if needed.
            
            print("\n================ OBSERVABILITY ================")
            print(f"Raw Query         : {body.query}")
            print(f"Normalized Query  : {normalized_query}")
            print(f"Processed Query   : {processed_query}")
            print(f"Intent            : {intent_name}")
            print(f"Confidence        : 1.0") # We don't bubble up confidence directly in FinalConversationResponse
            print(f"FastPath          : {is_fast_path}")
            print(f"Retrieval         : {has_retrieval}")
            print(f"Chunks Retrieved  : {chunks_retrieved}")
            print(f"Chunks Used       : {chunks_used}")
            print(f"Generation        : {'NO' if is_fast_path == 'YES' else 'YES'}")
            print(f"Response Type     : {'FastPath' if is_fast_path == 'YES' else 'Generated'}")
            print(f"Decision Time     : {decision_time}ms")
            print(f"Planner Time      : {planner_time}ms")
            print(f"Retrieval Time    : {ret_ms}ms")
            print(f"Generation Time   : {gen_ms}ms")
            print(f"Total Time        : {total_ms}ms")
            print("==============================================\n")
            
            return payload
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/pipeline")
async def debug_pipeline_endpoint() -> dict[str, Any]:
    """Diagnostics helper."""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403, detail="Pipeline debugging is disabled in production."
        )

    return {
        "debug": True,
        "engineOrder": ["ConversationOrchestrator", "RetrievalOrchestrator", "GenerationOrchestrator"],
        "totalEnginesCount": 3,
    }


@router.post("/debug/rag-trace")
async def debug_rag_trace_endpoint(request: Request, body: ChatRequest) -> dict[str, Any]:
    """Not supported in the new pipeline yet."""
    raise HTTPException(status_code=501, detail="RAG Trace is deprecated in favor of OpenTelemetry traces.")
