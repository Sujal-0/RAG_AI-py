"""Streaming Controller.

Coordinates the Server-Sent Events (SSE) or WebSockets architecture.
Wraps the final string generator into a consumable StreamChunk async generator.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.generation.dto.dtos import FormattedResponse, StreamChunk

logger = logging.getLogger("app")


class BaseStreamer(ABC):
    @abstractmethod
    async def stream(self, response: FormattedResponse) -> AsyncGenerator[StreamChunk, None]:
        pass


class SSEStreamer(BaseStreamer):
    """Generates Server-Sent Events from the response."""
    
    async def stream(self, response: FormattedResponse) -> AsyncGenerator[StreamChunk, None]:
        logger.info("Initializing SSE Stream", extra={"structured_log": True, "stage": "StreamingController"})
        
        # In a real scenario, this would yield tokens directly from the LLM via callback.
        # Since the Orchestrator currently buffers, we simulate chunking the final response.
        words = response.markdown_content.split(" ")
        
        for i, word in enumerate(words):
            is_done = (i == len(words) - 1)
            yield StreamChunk(content=word + " ", is_done=is_done)
            await asyncio.sleep(0.01) # Simulated network/token delay
            
        logger.info("SSE Stream Complete", extra={"structured_log": True, "stage": "StreamingController"})


class StreamingProviderFactory:
    """Dynamically loads the streaming protocol."""
    
    _instance: BaseStreamer | None = None
    
    @classmethod
    def get_provider(cls, provider_name: str) -> BaseStreamer:
        if cls._instance is None:
            if provider_name.lower() == "sse":
                cls._instance = SSEStreamer()
            else:
                logger.warning(f"Unknown stream provider '{provider_name}'. Defaulting to SSE.")
                cls._instance = SSEStreamer()
        return cls._instance
