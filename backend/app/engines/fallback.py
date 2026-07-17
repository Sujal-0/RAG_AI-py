"""Helpful Fallback engine.

Triggers when all prior engines pass without handling the query,
delivering a structured, helpful guide for users.
"""

import time

from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.intents import Intent
from app.pipeline.result import EngineResult


class FallbackEngine(BaseEngine):
    """Fallback engine delivering structured guidance responses."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()

        # Check for upstream database failures first
        db_error = context.metadata.get("rag_error_code")
        if db_error:
            context.intent = db_error
            context.response = "Our database is currently experiencing issues. Please try again later."
            reason_code = db_error
        else:
            context.intent = Intent.FALLBACK
            decision = context.metadata.get("decision")
            if decision == "RAG":
                context.response = "I couldn't find enough information in the uploaded documents."
            else:
                context.response = "I don't have information about that."
            reason_code = "FALLBACK_HELPFUL_OUTCOME"

        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

        metadata = {
            "intent": context.intent,
            "handled": True,
            "execution_ms": duration_ms,
        }

        return EngineResult(
            handled=True,
            reason_code=reason_code,
            metadata=metadata,
        )

    @property
    def name(self) -> str:
        return "Fallback"
