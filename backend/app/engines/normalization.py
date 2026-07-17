"""Normalization engine.

Cleans and normalizes query text through a 13-step deterministic pipeline.
"""

from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult
from app.utils.text import normalize_text, tokenize


class NormalizationEngine(BaseEngine):
    """Executes normalization pipeline and updates context query stages."""

    def execute(self, context: ConversationContext) -> EngineResult:
        # Run the deterministic normalization helper
        normalized = normalize_text(context.original_query)

        # Update context properties
        tokens = tokenize(normalized)
        
        # Apply fuzzy spelling correction based on system vocabulary
        from app.utils.text import fuzzy_correct_tokens
        corrected_tokens = fuzzy_correct_tokens(tokens)
        corrected_query = " ".join(corrected_tokens)
        
        context.normalized_query = corrected_query
        context.tokens = corrected_tokens
        context.remaining_query = corrected_query

        return EngineResult(handled=False, reason_code="NORMALIZATION_SUCCESS")

    @property
    def name(self) -> str:
        return "Normalization"
