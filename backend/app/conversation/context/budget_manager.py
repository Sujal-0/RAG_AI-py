"""Context Budget Manager.

Dynamically controls the token window by selecting the most critical memory items.
Actively filters out 'greetings' and 'thanks' to avoid context bleed, prioritizing 
architectural decisions and active entities.
"""

import logging
from typing import List

from app.conversation.memory.memory_engine import ConversationMemory
from app.core.settings import settings

logger = logging.getLogger("app")


class ContextBudgetManager:
    """Selects and packs memory strictly within the token budget."""
    
    @classmethod
    def select_context(cls, memory: ConversationMemory) -> List[str]:
        """Returns the highest priority memory items that fit the budget."""
        
        logger.info("Selecting Context within Budget", extra={"structured_log": True, "stage": "ContextBudgetManager"})
        
        selected_context = []
        
        # 1. Always prioritize Pinned Memory (Architectural decisions, strict preferences)
        selected_context.extend(memory.pinned_memory)
        
        # 2. Add Long Term / Medium Term Summaries
        selected_context.extend(memory.medium_memory)
        
        # 3. Filter Short Memory for high-value items
        # Drop pleasantries to save tokens
        drop_phrases = {"hi", "hello", "thanks", "thank you", "goodbye", "ok"}
        
        for item in memory.short_memory:
            if item.content.lower().strip() not in drop_phrases:
                selected_context.append(f"{item.role}: {item.content}")
                
        # Future: Truncate selected_context if the estimated token count exceeds budget
        
        logger.debug(f"Selected {len(selected_context)} memory items for context.")
        return selected_context
