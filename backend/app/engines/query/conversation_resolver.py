"""Conversation Resolver Engine.

Tracks conversational memory across turns to maintain topic continuity, 
detect pronouns (he/it/they), and retain entity context for the Query Rewriter.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("app")

@dataclass
class ConversationState:
    session_id: str
    previous_queries: list[str] = field(default_factory=list)
    previous_intents: list[str] = field(default_factory=list)
    active_entities: dict[str, list[str]] = field(default_factory=lambda: {
        "organizations": [], "people": [], "technologies": [], "dates": [], "locations": []
    })
    current_topic: str = "General"
    requires_resolution: bool = False


class ConversationResolver:
    """Maintains and resolves conversational state without modifying the query directly."""

    # Pronouns that indicate context dependency
    PRONOUNS = {"it", "they", "them", "he", "him", "she", "her", "this", "that", "these", "those"}

    @classmethod
    def resolve_state(
        cls, 
        current_query: str, 
        session_history: list[dict[str, str]],
        current_entities: dict[str, list[str]]
    ) -> ConversationState:
        """Analyze current query against history to determine context requirements."""
        
        state = ConversationState(session_id="default")
        
        if not session_history:
            return state

        # Extract recent context
        for msg in session_history[-3:]:  # Only care about recent context
            if msg.get("role") == "user":
                state.previous_queries.append(msg.get("content", ""))
                
        # Detect if resolution is needed based on pronouns or extreme brevity
        query_words = set(current_query.lower().split())
        has_pronouns = bool(cls.PRONOUNS.intersection(query_words))
        is_brief = len(query_words) <= 4
        
        if has_pronouns or is_brief:
            state.requires_resolution = True
            
        logger.debug(
            "Conversation State Resolved",
            extra={
                "structured_log": True, 
                "stage": "ConversationResolver",
                "requires_resolution": state.requires_resolution
            }
        )
        
        return state
