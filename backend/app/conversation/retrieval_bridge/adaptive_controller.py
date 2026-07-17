"""Adaptive Retrieval Controller.

Configures the downstream RetrievalOrchestrator dynamically based on the 
complexity and intent of the query. Replaces static magic numbers with 
adaptive scaling.
"""

import logging
from dataclasses import dataclass

from app.engines.query.query_analyzer import NormalizedQuery
from app.core.settings import settings

logger = logging.getLogger("app")


@dataclass
class AdaptiveRetrievalConfig:
    top_k: int
    neighbor_expansion: bool
    hybrid_search: bool
    multi_query: bool


class AdaptiveRetrievalController:
    """Tunes Retrieval parameters instantly based on complexity."""
    
    @classmethod
    def configure(cls, query: NormalizedQuery) -> AdaptiveRetrievalConfig:
        logger.info("Generating Adaptive Retrieval Configuration", extra={"structured_log": True, "stage": "AdaptiveRetrievalController"})
        
        # Default Baseline
        config = AdaptiveRetrievalConfig(
            top_k=5,
            neighbor_expansion=settings.conversation.enable_neighbor_expansion,
            hybrid_search=True,
            multi_query=False
        )
        
        if query.intent == "Comparison" or query.intent == "Architecture":
            config.top_k = 10
            config.multi_query = settings.conversation.enable_multi_query
            config.neighbor_expansion = True
            
        elif query.intent == "Definition":
            # Very direct answer needed, don't pollute context
            config.top_k = 3
            config.neighbor_expansion = False
            
        logger.info(
            "Configured Retrieval", 
            extra={"structured_log": True, "stage": "AdaptiveRetrievalController", "config": config.__dict__}
        )
        return config
