"""Retrieval Strategy Engine.

Dynamically selects the optimal retrieval strategy based on the query's intent 
and response expectations. Determines weights for BM25 vs Vector search, 
and sets strict metadata filter requirements.
"""

import logging
from dataclasses import dataclass
from app.core.settings import settings

logger = logging.getLogger("app")


@dataclass
class RetrievalStrategy:
    strategy_name: str
    dense_weight: float
    sparse_weight: float
    require_exact_metadata: bool
    target_chunk_types: list[str]
    expand_neighbors: bool
    top_k: int


class RetrievalStrategyEngine:
    """Determines how to fetch documents based on query understanding."""

    @classmethod
    def determine_strategy(
        cls, 
        intent: str, 
        response_expectation: str
    ) -> RetrievalStrategy:
        """Map intents and expectations to concrete search strategies."""
        
        strategy = RetrievalStrategy(
            strategy_name="Default",
            dense_weight=settings.retrieval.dense_weight,
            sparse_weight=settings.retrieval.sparse_weight,
            require_exact_metadata=False,
            target_chunk_types=["text", "table", "list", "code_block"],
            expand_neighbors=settings.retrieval.neighbor_expansion_enabled,
            top_k=settings.retrieval.top_k_hybrid
        )

        if intent == "Definition":
            strategy.strategy_name = "SemanticHeavy"
            strategy.dense_weight = 0.9
            strategy.sparse_weight = 0.1
            strategy.top_k = 10
            
        elif intent == "Comparison":
            strategy.strategy_name = "HighBreadth"
            strategy.top_k = 40
            strategy.expand_neighbors = True
            
        elif intent == "Workflow":
            strategy.strategy_name = "Sequential"
            strategy.expand_neighbors = True
            strategy.target_chunk_types = ["list", "text"]
            
        elif intent == "Policy":
            strategy.strategy_name = "MetadataStrict"
            strategy.require_exact_metadata = True
            strategy.dense_weight = 0.8
            strategy.sparse_weight = 0.2
            
        elif intent == "Architecture":
            strategy.strategy_name = "HeadingPriority"
            strategy.target_chunk_types = ["text", "code_block", "list"]
            
        elif intent == "Troubleshooting":
            strategy.strategy_name = "KeywordHeavy"
            strategy.dense_weight = 0.3
            strategy.sparse_weight = 0.7
            
        if response_expectation == "table":
            strategy.target_chunk_types = ["table"]
            strategy.expand_neighbors = False
            
        logger.info(
            "Strategy Selected",
            extra={
                "structured_log": True, 
                "stage": "RetrievalStrategyEngine", 
                "strategy": strategy.strategy_name,
                "dense_weight": strategy.dense_weight,
                "sparse_weight": strategy.sparse_weight
            }
        )
        
        return strategy
