"""Empty input engine.

Intercepts queries that resolve to empty or whitespace-only strings
after normalization steps are executed.
"""

import time

from app.configs.responses import EMPTY_INPUT_RESPONSES
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.intents import Intent
from app.pipeline.result import EngineResult
from app.utils.response import select_response


class EmptyInputEngine(BaseEngine):
    """Detects and handles empty, whitespace-only, or symbol-only inputs."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()
        raw = context.original_query or ""
        import re
        cleaned_raw = re.sub(r"[\s\u200b\u200c\u200d\ufeff]+", "", raw)
        if not cleaned_raw:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            # Resolve response string
            responses_dict = {"default": EMPTY_INPUT_RESPONSES}
            resolved_response = select_response("default", responses_dict, context)

            context.intent = Intent.EMPTY_INPUT
            context.response = resolved_response

            metadata = {
                "intent": Intent.EMPTY_INPUT,
                "handled": True,
                "reason_code": "EMPTY_INPUT_HANDLED",
                "confidence": 1.0,
                "matched_rule": "empty_or_stripped_symbols",
                "matched_alias": "",
                "flow": "PURE",
                "execution_ms": duration_ms,
                "remaining_query": "",
            }

            return EngineResult(
                handled=True,
                reason_code="EMPTY_INPUT_HANDLED",
                metadata=metadata,
            )

        return EngineResult(handled=False, reason_code="EMPTY_INPUT_CHECK_PASSED")

    @property
    def name(self) -> str:
        return "EmptyInput"
