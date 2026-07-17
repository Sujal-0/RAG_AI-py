"""Profanity filter engine.

Checks queries against a predefined list of profanity and abusive terms.
Routes directly to a fallback response if profanity is detected, protecting downstream engines.
"""

from typing import Any
import re
from app.pipeline.base import BaseEngine, EngineResult
from app.pipeline.context import ConversationContext


PROFANITY_LIST = {
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "cunt",
    "dick",
    "bastard",
    "motherfucker",
    "whore",
    "slut",
    "crap",
    "idiot",
    "stupid",
    "dumb",
    "gandu",
    "gaandu",
    "gendu",
    "bhenchod",
}


class ProfanityEngine(BaseEngine):
    """Detects abusive language and short-circuits the pipeline."""

    @property
    def name(self) -> str:
        return "PROFANITY_ENGINE"

    def execute(self, context: ConversationContext) -> EngineResult:
        """Check for bad words in the normalized query."""
        if not context.normalized_query:
            return EngineResult(handled=False, reason_code="PROFANITY_SKIPPED")

        words = set(re.findall(r"\b[a-zA-Z]+\b", context.normalized_query.lower()))

        overlap = words.intersection(PROFANITY_LIST)

        if overlap:
            context.response = (
                "I am a professional assistant. Please use appropriate language."
            )
            context.intent = "PROFANITY"
            return EngineResult(
                handled=True,
                reason_code="PROFANITY_DETECTED",
                metadata={"abusive_words_detected": list(overlap)},
            )

        return EngineResult(handled=False, reason_code="PROFANITY_CLEAR")
