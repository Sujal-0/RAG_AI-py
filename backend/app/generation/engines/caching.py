"""Response Cache.

Abstracts semantic caching for exact or highly similar queries to bypass 
the entire retrieval and generation pipeline. Future-ready for Redis.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from app.generation.dto.dtos import FinalResponse
from app.core.settings import settings

logger = logging.getLogger("app")


class BaseResponseCache(ABC):
    @abstractmethod
    def get(self, query: str) -> Optional[FinalResponse]:
        pass

    @abstractmethod
    def set(self, query: str, response: FinalResponse) -> None:
        pass


class InMemoryResponseCache(BaseResponseCache):
    """Simple in-memory dictionary cache for the MVP/Testing phase."""
    
    def __init__(self):
        self._cache = {}
        
    def get(self, query: str) -> Optional[FinalResponse]:
        if not settings.generation.response_cache_enabled:
            return None
            
        norm_query = query.lower().strip()
        hit = self._cache.get(norm_query)
        if hit:
            logger.info("Cache Hit", extra={"structured_log": True, "stage": "ResponseCache"})
        return hit

    def set(self, query: str, response: FinalResponse) -> None:
        if not settings.generation.response_cache_enabled:
            return
            
        norm_query = query.lower().strip()
        # Ensure we don't cache streams as they are single-use generators
        if response.stream is None:
            self._cache[norm_query] = response
            logger.info("Response Cached", extra={"structured_log": True, "stage": "ResponseCache"})


class ResponseCacheFactory:
    """Dynamically loads the cache provider."""
    
    _instance: BaseResponseCache | None = None
    
    @classmethod
    def get_provider(cls) -> BaseResponseCache:
        if cls._instance is None:
            # Future: add RedisResponseCache logic here based on settings
            cls._instance = InMemoryResponseCache()
        return cls._instance
