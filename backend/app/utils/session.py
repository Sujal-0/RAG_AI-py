import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class ConversationState:
    session_id: str
    name: Optional[str] = None
    greeting_count: int = 0
    last_interaction: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Advanced Conversational Memory
    active_document: Optional[str] = None
    active_topic: Optional[str] = None
    active_heading: Optional[str] = None
    active_department: Optional[str] = None
    active_company: Optional[str] = None
    active_entities: List[str] = field(default_factory=list)
    previous_retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    previous_answer_summary: Optional[str] = None
    previous_user_intent: Optional[str] = None
    pending_clarification: Optional[str] = None
    unanswered_references: List[str] = field(default_factory=list)
    follow_up_confidence: float = 0.0
    
    # History
    history: List[tuple[str, str]] = field(default_factory=list)
    last_context: Optional[Dict[str, Any]] = None
    is_compressed: bool = False
    compressed_summary: Optional[str] = None


class SessionStore:
    _lock = threading.Lock()
    _sessions: Dict[str, ConversationState] = {}
    
    # Configurable compression threshold (in turns)
    COMPRESSION_THRESHOLD_TURNS = 10

    @classmethod
    def get(cls, session_id: str) -> Dict[str, Any]:
        """Retrieve full session state as a dictionary for backwards compatibility."""
        with cls._lock:
            state = cls._get_or_create_unlocked(session_id)
            return state.__dict__

    @classmethod
    def set(cls, session_id: str, data: Dict[str, Any]) -> None:
        """Overwrite full session state."""
        with cls._lock:
            state = cls._get_or_create_unlocked(session_id)
            for k, v in data.items():
                if hasattr(state, k):
                    setattr(state, k, v)

    @classmethod
    def get_state(cls, session_id: str) -> ConversationState:
        """Retrieve the typed ConversationState object."""
        with cls._lock:
            return cls._get_or_create_unlocked(session_id)

    @classmethod
    def set_name(cls, session_id: str, name: str) -> None:
        """Set person name in the session."""
        with cls._lock:
            sess = cls._get_or_create_unlocked(session_id)
            sess.name = name

    @classmethod
    def get_name(cls, session_id: str) -> Optional[str]:
        """Get person name from the session."""
        with cls._lock:
            return cls._sessions.get(session_id, ConversationState(session_id=session_id)).name

    @classmethod
    def increment_greeting_count(cls, session_id: str) -> int:
        """Increment greeting counter."""
        with cls._lock:
            sess = cls._get_or_create_unlocked(session_id)
            sess.greeting_count += 1
            return sess.greeting_count

    @classmethod
    def get_greeting_count(cls, session_id: str) -> int:
        """Get greeting counter."""
        with cls._lock:
            return cls._sessions.get(session_id, ConversationState(session_id=session_id)).greeting_count

    @classmethod
    def set_last_interaction(cls, session_id: str, timestamp: float) -> None:
        """Set last interaction epoch timestamp."""
        with cls._lock:
            sess = cls._get_or_create_unlocked(session_id)
            sess.last_interaction = timestamp

    @classmethod
    def get_last_interaction(cls, session_id: str) -> Optional[float]:
        """Get last interaction epoch timestamp."""
        with cls._lock:
            return cls._sessions.get(session_id, ConversationState(session_id=session_id)).last_interaction

    @classmethod
    def set_metadata(cls, session_id: str, metadata: Dict[str, Any]) -> None:
        """Set session metadata dictionary."""
        with cls._lock:
            sess = cls._get_or_create_unlocked(session_id)
            sess.metadata = metadata

    @classmethod
    def get_metadata(cls, session_id: str) -> Dict[str, Any]:
        """Get session metadata dictionary."""
        with cls._lock:
            return cls._sessions.get(session_id, ConversationState(session_id=session_id)).metadata

    @classmethod
    def clear(cls) -> None:
        """Clear all active sessions (useful for tests)."""
        with cls._lock:
            cls._sessions.clear()

    @classmethod
    def set_last_context(cls, session_id: str, query: str, chunks: List[Dict[str, Any]], intent: str, topic: Optional[str] = None) -> None:
        """Cache last retrieved vector search context."""
        with cls._lock:
            sess = cls._get_or_create_unlocked(session_id)
            sess.last_context = {
                "query": query,
                "chunks": chunks,
                "intent": intent
            }
            # Also update Advanced State
            sess.previous_retrieved_chunks = chunks
            sess.previous_user_intent = intent
            if chunks:
                sess.active_document = chunks[0].get("filename")
                sess.active_heading = chunks[0].get("heading") or chunks[0].get("section")
                
            if topic:
                sess.active_topic = topic
            else:
                # Extract basic topic heuristically
                if "policy" in query.lower():
                    sess.active_topic = "Policy"
                elif "projects" in query.lower() or "services" in query.lower():
                    sess.active_topic = "Company Info"

    @classmethod
    def get_last_context(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve last cached vector search context."""
        with cls._lock:
            return cls._sessions.get(session_id, ConversationState(session_id=session_id)).last_context

    @classmethod
    def add_history(cls, session_id: str, role: str, text: str) -> None:
        """Add a message to the session's conversation history and trigger compression if needed."""
        with cls._lock:
            sess = cls._get_or_create_unlocked(session_id)
            sess.history.append((role, text))
            
            # Check for compression threshold
            max_messages = cls.COMPRESSION_THRESHOLD_TURNS * 2
            if len(sess.history) > max_messages:
                cls._compress_session_unlocked(sess)
            
            # If model role, update answer summary (heuristic approximation)
            if role == "model":
                sess.previous_answer_summary = text[:200] + "..." if len(text) > 200 else text

    @classmethod
    def set_compression_threshold(cls, turns: int) -> None:
        """Configure the conversation compression threshold dynamically."""
        cls.COMPRESSION_THRESHOLD_TURNS = max(1, turns)

    @classmethod
    def _compress_session_unlocked(cls, sess: ConversationState) -> None:
        """Compress old conversation history to save tokens."""
        if not sess.history:
            return
            
        old_history = sess.history[:-4]  # Keep last 2 turns
        sess.history = sess.history[-4:]
        
        # Simple heuristic compression for now (AI summary could be used but adds latency)
        topics = set()
        for role, text in old_history:
            if "policy" in text.lower(): topics.add("Policy")
            if "project" in text.lower(): topics.add("Projects")
        
        summary = f"User previously asked about: {', '.join(topics) if topics else 'various topics'}."
        sess.compressed_summary = summary
        sess.is_compressed = True
        
        # Clean up stale context
        sess.previous_retrieved_chunks = sess.previous_retrieved_chunks[:2]

    @classmethod
    def get_history(cls, session_id: str, limit: int = 5) -> List[tuple[str, str]]:
        """Retrieve the last N turns of conversation history."""
        with cls._lock:
            history = cls._sessions.get(session_id, ConversationState(session_id=session_id)).history
            messages_limit = limit * 2
            
            # If we have a compressed summary, we can inject it as system context in history
            sess = cls._sessions.get(session_id)
            if sess and sess.is_compressed and sess.compressed_summary:
                # We prepend a system note (some models treat role='user' with context)
                # But to maintain tuple typing and role compatibility, we'll return raw history.
                pass
                
            return history[-messages_limit:] if messages_limit > 0 else history

    @classmethod
    def _get_or_create_unlocked(cls, session_id: str) -> ConversationState:
        """Internal helper to find or instantiate a session without locking (caller must hold lock)."""
        if session_id not in cls._sessions:
            cls._sessions[session_id] = ConversationState(session_id=session_id)
        return cls._sessions[session_id]


