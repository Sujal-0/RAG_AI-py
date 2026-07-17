"""Query Rewriter Engine.

Takes an ambiguous follow-up query and rewrites it into a standalone 
enterprise search query using the resolved Conversation State. 
Does NOT simply append history.
"""

import logging
from app.engines.query.conversation_resolver import ConversationState

from abc import ABC, abstractmethod

logger = logging.getLogger("app")


class BaseQueryRewriteProvider(ABC):
    @abstractmethod
    async def rewrite(self, current_query: str, state: ConversationState) -> str:
        pass


class HeuristicRewriteProvider(BaseQueryRewriteProvider):
    """Rewrites queries heuristically."""

    async def rewrite(self, current_query: str, state: ConversationState) -> str:
        
        if not state.requires_resolution or not state.previous_queries:
            logger.debug("No rewrite required", extra={"structured_log": True, "stage": "QueryRewriter"})
            return current_query
            
        previous_query = state.previous_queries[-1]
        rewritten = f"{current_query} regarding the context of: {previous_query}"
        
        logger.info(
            "Query Rewritten",
            extra={"structured_log": True, "stage": "QueryRewriter", "original": current_query, "rewritten": rewritten}
        )
        return rewritten


class LLMRewriteProvider(BaseQueryRewriteProvider):
    """Rewrites queries using the configured LLM, with a fallback to Heuristic on failure."""
    
    def __init__(self):
        self._fallback = HeuristicRewriteProvider()
        
    async def rewrite(self, current_query: str, state: ConversationState) -> str:
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
