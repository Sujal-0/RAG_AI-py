"""Confidence Scoring Engine.

Aggregates retriever scores, cross-encoder scores, and context density 
to produce a final confidence categorization (HIGH, MEDIUM, LOW) to guide 
downstream LLM behavior (e.g., triggering fallbacks).
"""

import logging
from typing import Any

logger = logging.getLogger("app")


class ConfidenceEngine:
    """Calculates retrieval confidence."""

    @classmethod
    def calculate_confidence(cls, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        
        if not evidence:
            return {"level": "LOW", "score": 0.0, "reason": "No evidence retrieved."}

        # BGE logit heuristic
        max_score = max([item.get("rerank_score", 0.0) for item in evidence])
        
        if max_score > 2.0:
            level = "HIGH"
        elif max_score > 0.0:
            level = "MEDIUM"
        else:
            level = "LOW"
            
        logger.info(
            "Confidence Scored",
            extra={
                "structured_log": True, 
                "stage": "ConfidenceEngine", 
                "level": level,
                "score": max_score
            }
        )
            
        return {
            "level": level,
            "score": max_score,
            "reason": f"Max reranker logit is {max_score:.2f}"
        }
