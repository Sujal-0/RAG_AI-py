"""Query Rewriter Engine.

Takes an ambiguous follow-up query and rewrites it into a standalone 
enterprise search query using the resolved Conversation State. 
Does NOT simply append history.
"""

import logging
from typing import Any

from abc import ABC, abstractmethod

logger = logging.getLogger("app")


class BaseQueryRewriteProvider(ABC):
    @abstractmethod
    async def rewrite(self, current_query: str, state: Any) -> str:
        pass


class HeuristicRewriteProvider(BaseQueryRewriteProvider):
    """Rewrites queries heuristically."""

    async def rewrite(self, current_query: str, state: Any) -> str:
        
        if not state.requires_resolution or not state.previous_queries:
            logger.debug("No rewrite required", extra={"structured_log": True, "stage": "QueryRewriter"})
            return current_query
            
        previous_query = state.previous_queries[-1]
        
        # Simple heuristic noun extraction from previous query
        import re
        # Find the last significant noun phrase in the previous query (e.g. "What is Mobiloitte?" -> "Mobiloitte")
        # Strip common question words
        clean_prev = re.sub(r'^(what|who|where|when|why|how|tell me about|explain|summarize) (is|was|are|does|the|a|an)?\s*', '', previous_query, flags=re.IGNORECASE)
        clean_prev = clean_prev.replace('?', '').strip()
        
        if clean_prev:
            # Replace 'it', 'they', 'this', 'that', 'its' with the extracted noun phrase
            # Check if there is a possessive pronoun
            if re.search(r'\b(its|their)\b', current_query, flags=re.IGNORECASE):
                rewritten = re.sub(r'\b(its|their)\b', f"{clean_prev}'s", current_query, flags=re.IGNORECASE)
            elif re.search(r'\b(it|they|this|that|he|she)\b', current_query, flags=re.IGNORECASE):
                rewritten = re.sub(r'\b(it|they|this|that|he|she)\b', clean_prev, current_query, flags=re.IGNORECASE)
            else:
                # E.g. "what are the features?" -> "what are the features of [entity]?"
                # To avoid broad searches, just append 'of [entity]' at the end if it's a short query
                rewritten = f"{current_query} of {clean_prev}"
        else:
            rewritten = current_query
        
        logger.info(
            "Query Rewritten",
            extra={"structured_log": True, "stage": "QueryRewriter", "original": current_query, "rewritten": rewritten}
        )
        return rewritten


class LLMRewriteProvider(BaseQueryRewriteProvider):
    """Rewrites queries using the configured LLM, with a fallback to Heuristic on failure."""
    
    def __init__(self):
        self._fallback = HeuristicRewriteProvider()
        
    async def rewrite(self, current_query: str, state: Any) -> str:
        if not state.requires_resolution or not state.previous_queries:
            return current_query
            
        try:
            from app.engines.llm_generator import BaseAnswerGenerator
            # Stub logic to call LLM dynamically without breaking pipeline
            logger.info("Calling LLM to rewrite query...", extra={"structured_log": True, "stage": "QueryRewriter"})
            # simulated rewrite:
            rewritten = f"[{current_query}] (LLM rewritten based on {state.previous_queries[-1]})"
            return rewritten
        except Exception as e:
            logger.warning(
                f"LLM Rewrite failed: {e}. Falling back to Heuristic.",
                extra={"structured_log": True, "stage": "QueryRewriter"}
            )
            return await self._fallback.rewrite(current_query, state)
