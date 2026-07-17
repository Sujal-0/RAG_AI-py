"""Goodbye conversation engine.

Recognizes farewell intents, partitions the query into conversational components,
and manages flow transitions.
"""

import re
import time

from app.configs.goodbyes import GOODBYE_GROUPS, NOISE_TOKENS
from app.configs.responses import GOODBYE_RESPONSES
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.intents import Intent
from app.pipeline.result import EngineResult
from app.utils.conversation import is_business_query, is_noise_only
from app.utils.matcher import find_longest_match
from app.utils.response import select_response

# Confidence scoring thresholds
CONFIDENCE_EXACT = 1.00
CONFIDENCE_ALIAS = 0.98
CONFIDENCE_NORMALIZED = 0.97
CONFIDENCE_WEAK = 0.95


class GoodbyeEngine(BaseEngine):
    """Statelessly classifies and routes farewell-based conversation flows."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()

        decision = context.metadata.get("decision")
        has_goodbye = context.metadata.get("has_goodbye", False)
        if decision is not None and decision != "GOODBYE" and not has_goodbye:
            return EngineResult(handled=False, reason_code="GOODBYE_CHECK_PASSED")

        tokens = context.tokens
        input_query = context.original_query

        # 1. Search for matching goodbye aliases
        match = find_longest_match(tokens, GOODBYE_GROUPS)
        if not match:
            return EngineResult(handled=False, reason_code="GOODBYE_CHECK_PASSED")

        matched_term, canonical_goodbye, matched_indices = match

        # 2. Extract remaining tokens
        remaining_tokens = [
            tokens[i] for i in range(len(tokens)) if i not in matched_indices
        ]
        remaining_query = " ".join(remaining_tokens)

        # 3. Classify flow state
        flow = "PURE"
        handled = False
        reason_code = "GOODBYE_HANDLED"

        if not remaining_tokens:
            flow = "PURE"
            handled = True
            reason_code = f"GOODBYE_{canonical_goodbye.upper()}_HANDLED"
        elif is_noise_only(remaining_tokens) or all(
            t in NOISE_TOKENS for t in remaining_tokens
        ):
            flow = "PURE_WITH_NOISE"
            handled = True
            reason_code = f"GOODBYE_{canonical_goodbye.upper()}_NOISE_HANDLED"
        elif is_business_query(remaining_tokens):
            flow = "PREFIX_QUERY"
            handled = False
            reason_code = f"GOODBYE_{canonical_goodbye.upper()}_MIXED_CONTINUE"
        else:
            flow = "PREFIX_GARBAGE"
            handled = False
            reason_code = f"GOODBYE_{canonical_goodbye.upper()}_MIXED_CONTINUE"

        # 4. Calculate rule-based confidence
        confidence = CONFIDENCE_ALIAS
        if matched_term == canonical_goodbye:
            # Check if canonical term was exactly present in original raw query
            has_exact = re.search(
                rf"\b{re.escape(canonical_goodbye)}\b", input_query.lower()
            )
            confidence = CONFIDENCE_EXACT if has_exact else CONFIDENCE_ALIAS

        # Check for numeric suffix stripping (drops confidence)
        has_digits = any(char.isdigit() for char in input_query)
        if has_digits and matched_term in input_query.lower():
            confidence = CONFIDENCE_WEAK

        # 5. Route outcomes to context
        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

        metadata = {
            "intent": Intent.GOODBYE,
            "handled": handled,
            "reason_code": reason_code,
            "confidence": confidence,
            "matched_rule": f"goodbye_{canonical_goodbye}",
            "matched_alias": matched_term,
            "flow": flow,
            "execution_ms": duration_ms,
            "remaining_query": remaining_query,
        }

        if handled:
            context.intent = Intent.GOODBYE
            context.response = select_response(
                canonical_goodbye, GOODBYE_RESPONSES, context
            )
        else:
            # Mixed query transitions: store prefix and forward remaining payload
            context.metadata["goodbye_prefix_key"] = canonical_goodbye
            context.normalized_query = remaining_query
            context.tokens = remaining_tokens
            context.remaining_query = remaining_query

        return EngineResult(
            handled=handled,
            reason_code=reason_code,
            metadata=metadata,
        )

    @property
    def name(self) -> str:
        return "Goodbye"


class_name = GoodbyeEngine
