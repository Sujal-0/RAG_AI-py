"""Memory Engine.

Implements the multi-tier memory system (Working, Short, Medium, Long, Pinned).
Enforces Lazy Summarization to protect token budgets.
"""

import logging
from dataclasses import dataclass, field
from typing import List

from app.core.settings import settings

logger = logging.getLogger("app")


@dataclass
class MemoryItem:
    turn_id: int
    role: str
    content: str
    importance_score: float = 1.0


@dataclass
class ConversationMemory:
    working_memory: dict = field(default_factory=dict)
    short_memory: List[MemoryItem] = field(default_factory=list)
    medium_memory: List[str] = field(default_factory=list) # Summaries
    long_memory: List[str] = field(default_factory=list)
    pinned_memory: List[str] = field(default_factory=list)
    
    total_short_memory_tokens: int = 0


class MemoryEngine:
    """Manages tiered memory states and compression triggers."""
    
    @classmethod
    def add_interaction(cls, memory: ConversationMemory, user_query: str, ai_response: str) -> ConversationMemory:
        logger.debug("Adding interaction to memory", extra={"structured_log": True, "stage": "MemoryEngine"})
        
        turn = len(memory.short_memory) // 2
        
        memory.short_memory.append(MemoryItem(turn_id=turn, role="user", content=user_query))
        memory.short_memory.append(MemoryItem(turn_id=turn, role="assistant", content=ai_response))
        
        # Naive token estimation for triggering Lazy Summarization
        # 1 word ~ 1.3 tokens roughly
        memory.total_short_memory_tokens += int((len(user_query.split()) + len(ai_response.split())) * 1.3)
        
        if memory.total_short_memory_tokens > settings.conversation.summary_token_threshold:
            cls._trigger_lazy_summary(memory)
            
        return memory
        
    @classmethod
    def _trigger_lazy_summary(cls, memory: ConversationMemory) -> None:
        """Compresses short memory into medium memory."""
        logger.info(
            "Lazy Summary Triggered", 
            extra={"structured_log": True, "stage": "MemoryEngine", "tokens": memory.total_short_memory_tokens}
        )
        
        # In full implementation, this triggers an async LLM or Algorithmic summarizer
        # For now, we simulate shifting the oldest 50% out.
        memory.medium_memory.append("Summary of previous conversation turns.")
        memory.short_memory = memory.short_memory[len(memory.short_memory)//2:]
        memory.total_short_memory_tokens = memory.total_short_memory_tokens // 2
