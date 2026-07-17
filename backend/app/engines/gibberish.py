"""Gibberish engine.

Intercepts queries classified as probable gibberish or keyboard smashes,
delivering a polite request to rephrase.
"""

import time

from app.configs.responses import GIBBERISH_RESPONSES
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.intents import Intent
from app.pipeline.result import EngineResult
from app.utils.conversation import is_probable_gibberish
from app.utils.response import select_response


class GibberishEngine(BaseEngine):
    """Detects and handles keyboard smashes and meaningless input queries."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()
        decision = context.metadata.get("decision")
        if decision is not None and decision != "GIBBERISH":
            return EngineResult(handled=False, reason_code="GIBBERISH_CHECK_PASSED")

        query = context.normalized_query or ""
        original = context.original_query or ""

        from app.utils.conversation import get_token_gibberish_confidence
        tokens = [t for t in query.split(" ") if t]
        token_confidences = [get_token_gibberish_confidence(t) for t in tokens]
        max_token_conf = max(token_confidences) if token_confidences else 0.0
        gibberish_tokens = [tokens[i] for i, c in enumerate(token_confidences) if c >= 0.7]

        # Only handle if this is actually gibberish content:
        # - Decision engine routed here as GIBBERISH, OR
        # - Majority of tokens are gibberish AND max confidence is high
        gibberish_ratio = len(gibberish_tokens) / len(tokens) if tokens else 0.0
        is_gibberish = (
            (decision == "GIBBERISH")
            or (max_token_conf >= 0.7 and gibberish_ratio >= 0.5)
            or (len(tokens) == 1 and max_token_conf >= 0.7)
        )

        if is_gibberish:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            # Resolve response string
            responses_dict = {"default": GIBBERISH_RESPONSES}
            resolved_response = select_response("default", responses_dict, context)

            context.intent = Intent.GIBBERISH
            context.response = resolved_response
            context.metadata["confidence"] = 1.0

            metadata = {
                "intent": Intent.GIBBERISH,
                "handled": True,
                "reason_code": "GIBBERISH_HANDLED",
                "confidence": 1.0,
                "matched_rule": "keyboard_smash_or_consonants",
                "matched_alias": "",
                "flow": "PURE",
                "execution_ms": duration_ms,
                "remaining_query": "",
                "gibberish_tokens": gibberish_tokens,
                "max_token_confidence": max_token_conf,
                "gibberish_ratio": gibberish_ratio,
            }

            return EngineResult(
                handled=True,
                reason_code="GIBBERISH_HANDLED",
                metadata=metadata,
            )

        return EngineResult(handled=False, reason_code="GIBBERISH_CHECK_PASSED")

    @property
    def name(self) -> str:
        return "Gibberish"
