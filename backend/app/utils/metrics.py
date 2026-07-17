"""Enterprise Production Metrics Registry.

Aggregates system-wide telemetry for developer diagnostics and dashboards.
Tracks cache hit rates, provider fallbacks, latencies, and evidence confidence.
"""

import threading
import logging
from typing import Dict, Any

logger = logging.getLogger("app")

class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        
        self.total_queries = 0
        self.total_rag_queries = 0
        
        self.total_retrieval_latency = 0.0
        self.total_generation_latency = 0.0
        
        self.cache_hits = 0
        self.fallback_usage_count = 0
        self.total_chunks_used = 0
        self.total_evidence_confidence = 0.0

    def record_query(self, metadata: Dict[str, Any]) -> None:
        """Extract and aggregate telemetry from the processed query metadata."""
        with self._lock:
            self.total_queries += 1
            
            # Locate RAG telemetry in the trace if present
            trace = metadata.get("trace", [])
            rag_meta = None
            for entry in trace:
                if entry.get("engine") == "RAGRetrieval":
                    rag_meta = entry
                    break
                    
            if rag_meta and rag_meta.get("decision") == "RAG":
                self.total_rag_queries += 1
                
                # Retrieval Latency
                search_time = rag_meta.get("searchTimeMs", 0)
                embed_time = rag_meta.get("embeddingTimeMs", 0)
                self.total_retrieval_latency += (search_time + embed_time)
                
                # Generation Latency
                llm_latency = rag_meta.get("llmLatencyMs", 0)
                self.total_generation_latency += llm_latency
                
                # Cache hits
                if rag_meta.get("cacheHit", False):
                    self.cache_hits += 1
                    
                # Fallback usage
                if rag_meta.get("fallback_used", False):
                    self.fallback_usage_count += 1
                    
                # Average chunks & confidence
                self.total_chunks_used += rag_meta.get("chunkCount", 0)
                self.total_evidence_confidence += float(rag_meta.get("highest_similarity", 0.0))

    def get_metrics(self) -> Dict[str, Any]:
        """Return aggregated enterprise metrics."""
        with self._lock:
            rag_count = max(1, self.total_rag_queries)
            return {
                "total_queries": self.total_queries,
                "total_rag_queries": self.total_rag_queries,
                "cache_hit_rate": round(self.cache_hits / rag_count, 4),
                "fallback_rate": round(self.fallback_usage_count / rag_count, 4),
                "avg_retrieval_latency_ms": round(self.total_retrieval_latency / rag_count, 2),
                "avg_generation_latency_ms": round(self.total_generation_latency / rag_count, 2),
                "avg_chunks_used": round(self.total_chunks_used / rag_count, 2),
                "avg_evidence_confidence": round(self.total_evidence_confidence / rag_count, 4),
            }

global_metrics = MetricsRegistry()
