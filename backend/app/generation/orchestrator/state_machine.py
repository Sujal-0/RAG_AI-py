"""Generation State Machine.

Provides a robust state transition mechanism for tracking and logging the 
status of the generation pipeline. 
"""

import logging
from enum import Enum
from app.generation.dto.dtos import GenerationState

logger = logging.getLogger("app")


class GenerationStatus(str, Enum):
    """Explicit lifecycle states for generation."""
    BUILD_CONTEXT = "BUILD_CONTEXT"
    WINDOW_SELECTION = "WINDOW_SELECTION"
    COMPRESS_CONTEXT = "COMPRESS_CONTEXT"
    VALIDATE_EVIDENCE = "VALIDATE_EVIDENCE"
    COVERAGE_VALIDATION = "COVERAGE_VALIDATION"
    PLAN_RESPONSE = "PLAN_RESPONSE"
    BUILD_PROMPT = "BUILD_PROMPT"
    GENERATE_DRAFT = "GENERATE_DRAFT"
    VERIFY_RESPONSE = "VERIFY_RESPONSE"
    GENERATE_CITATIONS = "GENERATE_CITATIONS"
    POLISH_RESPONSE = "POLISH_RESPONSE"
    FORMAT_RESPONSE = "FORMAT_RESPONSE"
    QUALITY_CHECK = "QUALITY_CHECK"
    STREAM_RESPONSE = "STREAM_RESPONSE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class GenerationStateMachine:
    """Manages state transitions and logs metrics for observability."""
    
    @classmethod
    def transition(cls, state: GenerationState, new_status: GenerationStatus) -> None:
        """Transitions the pipeline state and logs the event."""
        
        previous_status = state.current_status
        state.current_status = new_status.value
        
        logger.info(
            f"Generation Transition: {previous_status} -> {new_status.value}",
            extra={
                "structured_log": True,
                "trace_id": state.trace_id,
                "stage": "StateMachine",
                "previous": previous_status,
                "current": new_status.value
            }
        )
