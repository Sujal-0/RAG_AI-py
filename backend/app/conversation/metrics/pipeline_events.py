"""Pipeline Events System.

Publishes major architectural transitions as deterministic events 
for tracking, webhooks, or asynchronous UI updates.
"""

import logging
from typing import Callable, List
from app.conversation.dto.dtos import ConversationEvent

logger = logging.getLogger("app")


class PipelineEventBus:
    """Simple pub/sub for pipeline execution tracking."""
    
    _subscribers: List[Callable[[ConversationEvent], None]] = []
    
    @classmethod
    def subscribe(cls, callback: Callable[[ConversationEvent], None]) -> None:
        cls._subscribers.append(callback)
        
    @classmethod
    def publish(cls, event: ConversationEvent) -> None:
        logger.info(
            f"Event Published: {event.event_type}", 
            extra={"structured_log": True, "trace_id": event.trace_id, "event": event.__dict__}
        )
        for sub in cls._subscribers:
            try:
                sub(event)
            except Exception as e:
                logger.error(f"Event subscriber failed: {e}")
