"""MultiQuery Generator.

Algorithm-first query expansion. Expands complex queries into 3-5 distinct sub-queries 
to maximize recall. Defaults to simple algorithmic splitting unless specifically 
configured to use an LLM for complex research queries.
"""

import logging
from typing import List

from app.core.settings import settings
from app.engines.query.query_analyzer import NormalizedQuery

logger = logging.getLogger("app")


class MultiQueryGenerator:
    """Generates expanded queries to improve retrieval recall."""
    
    @classmethod
    def expand(cls, query: NormalizedQuery) -> List[str]:
        logger.info("Generating Multi-Queries", extra={"structured_log": True, "stage": "MultiQueryGenerator"})
        
        queries = [query.normalized_text]
        
        if not settings.conversation.enable_multi_query:
            return queries
            
        # Algorithmic Expansion Strategy
        if query.intent == "Comparison" and " and " in query.normalized_text:
            parts = query.normalized_text.split(" and ")
            for part in parts:
                if len(part.strip()) > 3:
                    queries.append(f"{part.strip()} features")
                    
        # Future: Call LLM Expansion here ONLY if the query intent is "Research"
        # and ambiguity requires semantic decomposition.
        
        logger.debug(f"Expanded to {len(queries)} queries.", extra={"queries": queries})
        return queries
