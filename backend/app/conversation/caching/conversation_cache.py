"""Conversation Cache Platform.

Implements multi-tiered caching: Resolved Query Cache, Retrieval Cache, Generation Cache.
Defaults to InMemory but architected to inject Redis dynamically.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from app.core.settings import settings

logger = logging.getLogger("app")


class BaseCacheProvider(ABC):
    @abstractmethod
    def get(self, cache_tier: str, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, cache_tier: str, key: str, value: Any) -> None:
        pass


class InMemoryCacheProvider(BaseCacheProvider):
    """In-memory fallback cache."""
    
    def __init__(self):
        # Separate dictionaries per tier to avoid collision
        self._stores = {
            "resolved_query": {},
            "retrieval": {},
            "generation": {}
        }

    def get(self, cache_tier: str, key: str) -> Optional[Any]:
        if not settings.conversation.enable_caching:
            return None
        return self._stores.get(cache_tier, {}).get(key)

    def set(self, cache_tier: str, key: str, value: Any) -> None:
        if not settings.conversation.enable_caching:
            return
        if cache_tier in self._stores:
            self._stores[cache_tier][key] = value


class CachePlatform:
    """Facade for the underlying Cache Provider."""
    
    _provider: BaseCacheProvider = InMemoryCacheProvider() # Default
    
    @classmethod
    def check_resolved_query(cls, raw_query: str) -> Optional[str]:
        return cls._provider.get("resolved_query", raw_query.lower().strip())
        
    @classmethod
    def save_resolved_query(cls, raw_query: str, resolved_query: str) -> None:
        cls._provider.set("resolved_query", raw_query.lower().strip(), resolved_query)
