"""Pipeline query processing and response builder.

Orchestrates context creation, pipeline execution, and standard response serialization.
"""

from datetime import UTC, datetime
from typing import Any

from app.configs.responses import (
    GOODBYE_RESPONSES,
    GREETING_RESPONSES,
    SMALL_TALK_RESPONSES,
    THANKS_RESPONSES,
)
from app.pipeline.context import ConversationContext
from app.pipeline.executor import run_pipeline
from app.utils.logger import logger
from app.utils.response import select_response


FRIENDLY_INTENT_MAP = {
    "GREETING": "Greeting",
    "GOODBYE": "Goodbye",
    "THANKS": "Thanks",
    "SMALL_TALK": "Small Talk",
    "EMPTY_INPUT": "Fallback",
    "FALLBACK": "Fallback",
    "UNKNOWN": "Fallback",
    "COMPANY_OVERVIEW": "Company Information",
    "OFFICE_LOCATIONS": "Company Information",
    "CONTACT_DETAILS": "Company Information",
    "CULTURE": "Company Information",
    "COMPANY_VISION": "Company Information",
    "MISSION": "Company Information",
    "VISION_MISSION": "Company Information",
    "VALUES": "Company Information",
    "SERVICES": "Company Information",
    "SUPPORT": "Company Information",
    "AI_SERVICES": "Artificial Intelligence",
    "CLOUD_SERVICES": "Cloud Technologies",
    "WEB_DEVELOPMENT": "Company Information",
    "MOBILE_DEVELOPMENT": "Company Information",
    "BLOCKCHAIN": "Blockchain",
    "IOT": "Company Information",
    "CAREERS": "HR & Recruitment",
    "INTERNSHIP": "HR & Recruitment",
    "TRAINING": "HR Policies",
    "LEAVE_POLICY": "HR Policies",
    "SECURITY_POLICY": "Security & Compliance",
    "CLOUD": "Cloud Technologies",
    "AI": "Artificial Intelligence",
    "KNOWLEDGE_RETRIEVED": "Knowledge Retrieval",
    "COMPANY_INTENT": "Company Information",
}


def clean_greeting_prefix(prefix: str) -> str:
    """Strip question suffixes from greeting responses in mixed queries."""
    if not prefix:
        return prefix
    import re
    sentences = re.split(r'(?<=[.!?])\s+', prefix)
    if sentences:
        first = sentences[0].strip()
        if not first.endswith("?"):
            return first
    return prefix


def build_response(context: ConversationContext) -> dict[str, Any]:
    """Serialize ConversationContext into standard API response.

    Args:
        context: Context state after pipeline execution.

    Returns:
        Structured API dictionary output payload.
    """
    # 1. Resolve pure greeting responses if matched by GreetingEngine
    response_key = context.metadata.get("response_key")
    if response_key and not context.response:
        context.response = select_response(response_key, GREETING_RESPONSES, context)
        from app.utils.session import SessionStore
        name = SessionStore.get_name(context.session_id)
        if name:
            from app.utils.response import format_greeting_with_name
            context.response = format_greeting_with_name(context.response, response_key, name)

    # 2. Confidence-based intent routing for mixed queries
    greeting_prefix_key = context.metadata.get("greeting_prefix_key")
    thanks_prefix_key = context.metadata.get("thanks_prefix_key")
    small_talk_prefix_key = context.metadata.get("small_talk_prefix_key")
    goodbye_prefix_key = context.metadata.get("goodbye_prefix_key")

    greeting_confidence = context.metadata.get("greeting_confidence", 0.0)
    business_confidence = context.metadata.get("confidence", 0.0)
    has_business_match = context.response and context.intent not in ("FALLBACK", "UNKNOWN", "EMPTY_INPUT", "GIBBERISH")

    prefixes = []
    if greeting_prefix_key:
        prefix_res = select_response(greeting_prefix_key, GREETING_RESPONSES, context)
        from app.utils.session import SessionStore
        name = SessionStore.get_name(context.session_id)
        if name:
            from app.utils.response import format_greeting_with_name
            prefix_res = format_greeting_with_name(prefix_res, greeting_prefix_key, name)
        
        # Clean prefix if it is being merged with a business query
        if has_business_match:
            prefix_res = clean_greeting_prefix(prefix_res)
        
        # Route by confidence
        if context.response != prefix_res:
            if greeting_confidence >= 0.60 and business_confidence >= 0.60:
                # Both are high confidence, merge them
                prefixes.append(prefix_res)
            elif greeting_confidence > business_confidence and not has_business_match:
                context.response = prefix_res
                context.intent = "GREETING"
            elif business_confidence > greeting_confidence and has_business_match:
                # Business query dominates, skip greeting prefix
                pass
            elif has_business_match:
                # Both are meaningful: merge with natural paragraph spacing
                prefixes.append(prefix_res)

    if thanks_prefix_key:
        prefixes.append(select_response(thanks_prefix_key, THANKS_RESPONSES, context))
    if small_talk_prefix_key:
        prefixes.append(
            select_response(small_talk_prefix_key, SMALL_TALK_RESPONSES, context)
        )
    if goodbye_prefix_key:
        prefixes.append(select_response(goodbye_prefix_key, GOODBYE_RESPONSES, context))

    import inspect
    is_stream = inspect.isasyncgen(context.response)

    if prefixes and context.response and context.intent not in ("GIBBERISH", "ERROR"):
        combined_prefix = "\n\n".join(prefixes)
        
        if is_stream:
            # We must bind the original response generator
            original_stream = context.response
            async def prefix_stream_wrapper():
                yield combined_prefix + "\n\n"
                async for chunk in original_stream:
                    yield chunk
            context.response = prefix_stream_wrapper()
        else:
            context.response = f"{combined_prefix}\n\n{context.response}"
            
        if context.intent not in (
            "GREETING",
            "FALLBACK",
            "SMALL_TALK",
            "GOODBYE",
            "THANKS",
            "EMPTY_INPUT",
        ):
            context.intent = "COMPANY_INTENT"

    # Extract reasonCode from the last engine execution trace if available
    reason_code = None
    if context.trace:
        reason_code = context.trace[-1].get("reasonCode")

    # The request is handled if the last engine successfully short-circuited
    handled = False
    if context.trace:
        handled = context.trace[-1].get("handled", False)

    confidence = context.metadata.get("confidence")
    if confidence is None:
        if context.intent in ("GREETING", "GOODBYE", "THANKS", "EMPTY_INPUT", "GIBBERISH"):
            confidence = 1.00
        else:
            confidence = 0.00

    # Determine friendly Display Intent Name
    display_intent = FRIENDLY_INTENT_MAP.get(
        context.intent,
        context.intent.replace("_", " ").title() if context.intent else "Fallback"
    )

    return {
        "success": True,
        "intent": context.intent,
        "displayIntent": display_intent,
        "confidence": confidence,
        "answer": context.response,
        "reasonCode": reason_code,
        "normalizedQuery": context.normalized_query,
        "resolvedQuery": context.resolved_query or context.normalized_query,
        "matchedKeywords": context.metadata.get("matched_keywords", []),
        "requestId": context.request_id,
        "timestamp": context.timestamp,
        "trace": context.trace,
        "metadata": {
            **context.metadata,
            "rawQuery": context.raw_query,
            "handled": handled,
            "reasonCode": reason_code,
            "trace": context.trace,
        },
    }


def process_query(
    original_query: str,
    session_id: str,
    request_id: str,
    metadata: dict[str, Any] = None,
) -> dict[str, Any]:
    """Process an incoming user query statelessly through the conversation pipeline.

    Args:
        original_query: Raw input text from the client.
        session_id: Unique identifier tracing user conversation session.
        request_id: Traced identifier for the HTTP request.
        metadata: Optional initial metadata dictionary.

    Returns:
        Structured API dictionary outcome.
    """
    # Create fresh context frame for this request
    context = ConversationContext(
        request_id=request_id,
        session_id=session_id,
        original_query=original_query,
    )
    if metadata:
        context.metadata.update(metadata)

    try:
        # Run sequential engines execution loop
        context = run_pipeline(context)
        response_payload = build_response(context)
        
        # Record production telemetry
        from app.utils.metrics import global_metrics
        global_metrics.record_query(response_payload.get("metadata", {}))
        
        return response_payload
    except Exception as e:
        logger.error(
            "Fatal error processing query: %s",
            str(e),
            exc_info=True,
            extra={"request_id": request_id},
        )
        # Return fallback error schema
        return {
            "success": False,
            "intent": "ERROR",
            "confidence": 0.00,
            "answer": "An unexpected error occurred during query processing.",
            "normalizedQuery": None,
            "resolvedQuery": None,
            "matchedKeywords": [],
            "requestId": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "trace": [],
            "metadata": {"error": str(e), "reasonCode": "FATAL_PIPELINE_ERROR"},
        }
