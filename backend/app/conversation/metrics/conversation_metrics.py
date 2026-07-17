"""Conversation Metrics Engine.

Centralized aggregator for latency, LLM skips, token budgets, and 
execution costs for the conversation lifecycle.
"""

import logging
import time
from contextlib import contextmanager

from app.conversation.dto.dtos import ConversationMetrics

logger = logging.getLogger("app")


class MetricsTracker:
    """Manages real-time accumulation of Conversation Metrics."""
    
    @classmethod
    @contextmanager
    def track_latency(cls, metrics: ConversationMetrics, stage_name: str):
        """Context manager to cleanly record execution latency per stage."""
        start = time.time()
        try:
            yield
        finally:
            duration = int((time.time() - start) * 1000)
            metrics.duration_ms[stage_name] = duration
            
            # Enforce <25ms budget constraint visually in logs
            if duration > 25 and stage_name in ["ReferenceResolution", "DecisionEngine"]:
                logger.warning(
                    f"Latency Budget Violation! Stage: {stage_name} took {duration}ms (Limit: 25ms)",
                    extra={"structured_log": True, "stage": "MetricsTracker"}
                )
