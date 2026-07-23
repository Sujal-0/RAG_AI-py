"""Conversation Memory Manager.

Enterprise in-memory conversation storage for managing follow-up turns 
and conversation history without requiring a database connection immediately.
"""

import logging
from typing import Dict
from app.conversation.dto.dtos import ConversationSession

logger = logging.getLogger("app")

_SESSION_STORE: Dict[str, ConversationSession] = {}

class MemoryManager:
    """Manages conversational turns and history."""
    
    @classmethod
    def get_session(cls, session_id: str) -> ConversationSession:
        if session_id not in _SESSION_STORE:
            logger.info(f"Creating new session memory for {session_id}")
            _SESSION_STORE[session_id] = ConversationSession(session_id=session_id, trace_id="", mode="standard")
        return _SESSION_STORE[session_id]
        
    @classmethod
    def append_turn(cls, session_id: str, query: str, answer: str):
        session = cls.get_session(session_id)
        # Store user and assistant messages
        session.short_memory.append({"role": "user", "content": query})
        session.short_memory.append({"role": "assistant", "content": answer})
        
        # Keep only the last 10 turns (20 messages)
        if len(session.short_memory) > 20:
            session.short_memory = session.short_memory[-20:]
            
        logger.debug(f"Appended turn to session {session_id}. History size: {len(session.short_memory)}")
