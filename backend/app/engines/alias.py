"""Alias resolver engine.

Deterministically replaces synonyms and slang with canonical tokens
using longest-match boundary-safe replacements.
"""

import re
import time

from app.configs.aliases import ALIASES
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult


class AliasEngine(BaseEngine):
    """Orchestrates longest-match alias replacement on the query."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()

        query = context.normalized_query or ""
        if not query.strip():
            context.resolved_query = query
            return EngineResult(handled=False, reason_code="ALIAS_EMPTY_INPUT")

        # Sort alias patterns: multi-word phrases first, then length descending
        sorted_aliases = sorted(
            ALIASES.items(),
            key=lambda x: (len(x[0].split(" ")), len(x[0])),
            reverse=True,
        )

        resolved = query
        matched_aliases = []

        # Protect known conversational phrases from being modified by alias replacements
        from app.configs.greetings import GREETING_GROUPS
        from app.configs.goodbyes import GOODBYE_GROUPS
        from app.configs.thanks import THANKS_GROUPS
        from app.configs.small_talk import SMALL_TALK_GROUPS

        conversational_phrases = []
        for groups in (GREETING_GROUPS, GOODBYE_GROUPS, THANKS_GROUPS, SMALL_TALK_GROUPS):
            for phrases in groups.values():
                for phrase in phrases:
                    if phrase.lower().strip():
                        conversational_phrases.append(phrase.lower().strip())

        # Sort conversational phrases by word count / length descending to protect longest phrases first
        conversational_phrases = sorted(
            list(set(conversational_phrases)),
            key=lambda x: (len(x.split(" ")), len(x)),
            reverse=True,
        )

        placeholders = {}
        resolved_masked = resolved
        for idx, phrase in enumerate(conversational_phrases):
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, resolved_masked, flags=re.IGNORECASE):
                placeholder = f"__CONV_PHRASE_{idx}__"
                matched_span = re.search(pattern, resolved_masked, flags=re.IGNORECASE).group(0)
                placeholders[placeholder] = matched_span
                resolved_masked = re.sub(pattern, placeholder, resolved_masked, flags=re.IGNORECASE)

        # Perform boundary-safe regex replacements on the masked query
        for alias_phrase, canonical in sorted_aliases:
            pattern = rf"\b{re.escape(alias_phrase)}\b"
            if re.search(pattern, resolved_masked, flags=re.IGNORECASE):
                resolved_masked = re.sub(pattern, canonical, resolved_masked, flags=re.IGNORECASE)
                matched_aliases.append(alias_phrase)

        # Restore the protected conversational phrases
        for placeholder, original in placeholders.items():
            resolved_masked = resolved_masked.replace(placeholder, original)
        resolved = resolved_masked

        # Update context properties
        context.resolved_query = resolved
        # Update context tokens based on the new resolved query structure
        context.tokens = [t for t in resolved.split(" ") if t.strip()]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

        metadata = {
            "resolved_query": resolved,
            "matched_aliases": matched_aliases,
            "execution_ms": duration_ms,
        }

        # Stash in trace metadata
        context.metadata["resolved_query"] = resolved
        context.metadata["matched_aliases"] = matched_aliases

        return EngineResult(
            handled=False,
            reason_code="ALIAS_RESOLUTION_COMPLETED",
            metadata=metadata,
        )

    @property
    def name(self) -> str:
        return "Alias"
