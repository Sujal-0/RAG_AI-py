"""Validation engine placeholder."""

from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult


class ValidationEngine(BaseEngine):
    """Placeholder for request input validation engine."""

    def execute(self, context: ConversationContext) -> EngineResult:
        return EngineResult(handled=False, reason_code="VALIDATION_CHECK_PASSED")

    @property
    def name(self) -> str:
        return "Validation"
