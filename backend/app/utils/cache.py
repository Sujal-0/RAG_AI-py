"""Production Cache with TTL, LRU eviction, and multi-factor key hashing."""
import hashlib
import time
from collections import OrderedDict
from typing import Any, Optional


class ResponseCache:
    """Semantic Cache 2.0 supporting Exact and Evidence-based Near-Duplicate matching."""
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        # Main cache: exact keys -> payload
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        # Secondary index: evidence_hash -> list of keys (for near-duplicate matching)
        self.evidence_index: dict[str, list[str]] = {}
        # Level 1 Exact Index: query -> cache_key (for pre-retrieval matching)
        self.exact_query_index: dict[str, str] = {}

    def _generate_key(self, query: str, evidence_hash: str, prompt_version: str, 
                      doc_version: str, embed_version: str,
                      context_hash: str = "", language: str = "en", 
                      provider: str = "default", style: str = "standard") -> str:
        key_str = f"{query}|{evidence_hash}|{prompt_version}|{doc_version}|{embed_version}|{context_hash}|{language}|{provider}|{style}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def _is_failure_response(self, data: Any) -> bool:
        if not isinstance(data, str):
            return False
        dl = data.lower()
        if "unknown query" in dl or "information unavailable" in dl or "couldn't find enough information" in dl:
            return True
        if "fallback" in dl or "timeout" in dl or "clarification" in dl:
            return True
        if "database" in dl or "failure" in dl or "error" in dl:
            return True
        return False

    def get_exact(self, query: str) -> Any:
        """Level 1 Cache: Pre-retrieval exact query match."""
        query_clean = query.lower().strip()
        if query_clean in self.exact_query_index:
            key = self.exact_query_index[query_clean]
            if key in self.cache:
                entry = self.cache[key]
                if self._is_failure_response(entry["data"]):
                    self._evict(key)
                    return None
                if time.time() - entry["timestamp"] <= self.ttl_seconds:
                    self.cache.move_to_end(key)
                    return entry["data"]
                else:
                    self._evict(key)
        return None

    def get(self, query: str, evidence_hash: str, prompt_version: str, doc_version: str, embed_version: str,
            context_hash: str = "", language: str = "en", provider: str = "default", style: str = "standard") -> Any:
        
        # 1. Exact Match
        key = self._generate_key(query, evidence_hash, prompt_version, doc_version, embed_version, context_hash, language, provider, style)
        if key in self.cache:
            entry = self.cache[key]
            if self._is_failure_response(entry["data"]):
                self._evict(key)
            elif time.time() - entry["timestamp"] <= self.ttl_seconds:
                self.cache.move_to_end(key)
                return entry["data"]
            else:
                self._evict(key)
                
        # 2. Near-Duplicate / Semantic Evidence Match
        if evidence_hash in self.evidence_index:
            for potential_key in reversed(self.evidence_index[evidence_hash]):
                if potential_key in self.cache:
                    entry = self.cache[potential_key]
                    if self._is_failure_response(entry["data"]):
                        self._evict(potential_key)
                        continue
                    if time.time() - entry["timestamp"] <= self.ttl_seconds:
                        meta = entry["meta"]
                        if (meta["prompt"] == prompt_version and meta["doc"] == doc_version and 
                            meta["lang"] == language and meta["style"] == style and meta["context"] == context_hash):
                            self.cache.move_to_end(potential_key)
                            return entry["data"]
            
        return None

    def set(self, query: str, evidence_hash: str, prompt_version: str, doc_version: str, embed_version: str, data: Any,
            context_hash: str = "", language: str = "en", provider: str = "default", style: str = "standard") -> None:
        
        if self._is_failure_response(data):
            return
            
        key = self._generate_key(query, evidence_hash, prompt_version, doc_version, embed_version, context_hash, language, provider, style)
        
        # Enforce LRU Max Size
        if len(self.cache) >= self.max_size:
            lru_key = next(iter(self.cache))
            self._evict(lru_key)
            
        self.cache[key] = {
            "timestamp": time.time(),
            "data": data,
            "meta": {
                "prompt": prompt_version,
                "doc": doc_version,
                "lang": language,
                "style": style,
                "context": context_hash,
                "evidence": evidence_hash
            }
        }
        
        query_clean = query.lower().strip()
        self.exact_query_index[query_clean] = key
        
        if evidence_hash not in self.evidence_index:
            self.evidence_index[evidence_hash] = []
        if key not in self.evidence_index[evidence_hash]:
            self.evidence_index[evidence_hash].append(key)

    def _evict(self, key: str) -> None:
        if key in self.cache:
            entry = self.cache[key]
            ev_hash = entry["meta"]["evidence"]
            del self.cache[key]
            if ev_hash in self.evidence_index and key in self.evidence_index[ev_hash]:
                self.evidence_index[ev_hash].remove(key)
                if not self.evidence_index[ev_hash]:
                    del self.evidence_index[ev_hash]
            
            # Cleanup exact query index
            for q, k in list(self.exact_query_index.items()):
                if k == key:
                    del self.exact_query_index[q]

    def clear(self) -> None:
        self.cache.clear()
        self.evidence_index.clear()
        self.exact_query_index.clear()

response_cache = ResponseCache()


