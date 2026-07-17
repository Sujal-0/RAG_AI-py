"""Reference Resolver.

Resolves ambiguous pronouns and conversational references (e.g., 'it', 'that document') 
using algorithmic graph lookups *before* ever touching an LLM.
"""

import logging
from typing import Tuple

from app.core.settings import settings
from app.conversation.graph.conversation_graph import ConversationGraph

logger = logging.getLogger("app")


class ReferenceResolver:
    """Algorithm-first resolution to hit <10ms targets."""
    
    PRONOUNS = {"it", "he", "she", "they", "this", "that", "those", "these", "them"}
    
    @classmethod
    def resolve(cls, query: str, graph: ConversationGraph) -> Tuple[str, bool]:
        """
        Attempts to resolve references in the query.
        Returns (resolved_query, needs_clarification)
        """
        logger.info("Resolving References", extra={"structured_log": True, "stage": "ReferenceResolver"})
        
        words = query.lower().split()
        contains_pronoun = any(word in cls.PRONOUNS for word in words)
        
        if not contains_pronoun:
            return query, False
            
        # 1. Algorithmic Fallback: Substitute "it" or "that" with the Active Entity
        active_entity = graph.get_most_recent_entity()
        
        if active_entity:
            # Very naive string replacement for MVP algorithm (e.g. "what is it" -> "what is [Entity]")
            # A true implementation would use a POS tagger to identify the exact syntactic pronoun target.
            resolved = query
            for p in [" it", " that", " this"]:
                if p in resolved.lower():
                    resolved = resolved.replace(p, f" {active_entity.value}", 1)
                    
            logger.info(
                f"Resolved algorithmically using entity: {active_entity.value}", 
                extra={"structured_log": True, "stage": "ReferenceResolver"}
            )
            return resolved, False
            
        # 2. Ambiguity Fallback
        # If there's a pronoun but NO active entity in the graph, we are ambiguous.
        logger.warning(
            "Ambiguous Reference Detected. Clarification required.", 
            extra={"structured_log": True, "stage": "ReferenceResolver"}
        )
        return query, True
