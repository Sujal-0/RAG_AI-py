"""Response Strategy Engine.

Determines the required formatting and layout structure of the response 
*before* Generation executes, removing the need for the LLM to guess.
"""

import logging

from app.engines.query.query_analyzer import NormalizedQuery

logger = logging.getLogger("app")


class ResponseStrategyEngine:
    """Classifies the structural strategy required for Generation."""
    
    @classmethod
    def determine_strategy(cls, query: NormalizedQuery) -> str:
        logger.info("Determining Response Strategy", extra={"structured_log": True, "stage": "ResponseStrategyEngine"})
        
        intent = query.intent
        
        strategy_map = {
            "Comparison": "Comparison Table",
            "Procedure": "Workflow",
            "Architecture": "Architecture Overview",
            "Policy": "Checklist",
            "Troubleshooting": "Debug Steps",
            "Definition": "Standard Definition"
        }
        
        selected_strategy = strategy_map.get(intent, "Standard")
        
        logger.info(
            f"Strategy selected: {selected_strategy}", 
            extra={"structured_log": True, "stage": "ResponseStrategyEngine"}
        )
        return selected_strategy
