"""Intent Detection Engine.

Classifies the user query against strict enterprise intents to inform 
downstream retrieval strategies and metadata filters.
"""

import logging
import re

logger = logging.getLogger("app")

class IntentDetectionEngine:
    """Detects deterministic intents from queries."""

    INTENTS = {
        "Definition": [r"\bwhat is\b", r"\bdefine\b", r"\bmeaning of\b"],
        "Comparison": [r"\bcompare\b", r"\bdifference between\b", r"\bvs\b", r"\bversus\b"],
        "Workflow": [r"\bhow to\b", r"\bstep[s]?\b", r"\bprocess\b", r"\bworkflow\b", r"\bguide\b"],
        "Architecture": [r"\barchitecture\b", r"\bsystem design\b", r"\bcomponent\b", r"\bdiagram\b"],
        "Troubleshooting": [r"\berror\b", r"\bfix\b", r"\bissue\b", r"\bbug\b", r"\bnot working\b", r"\btroubleshoot\b"],
        "FAQ": [r"\bfaq\b", r"\bquestions\b"],
        "Policy": [r"\bpolicy\b", r"\brule[s]?\b", r"\bcompliance\b", r"\bguideline[s]?\b", r"\ballowed\b"],
        "Timeline": [r"\bwhen\b", r"\btimeline\b", r"\bdate[s]?\b", r"\bschedule\b"],
        "Summary": [r"\bsummarize\b", r"\bsummary\b", r"\btl;dr\b", r"\boverview\b"]
    }

    @classmethod
    def detect_intent(cls, query: str) -> str:
        """Analyze query and return matching intent, or 'Unknown'."""
        query_lower = query.lower()
        
        for intent, patterns in cls.INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    logger.info(
                        "Intent Detected",
                        extra={"structured_log": True, "stage": "IntentDetectionEngine", "intent": intent}
                    )
                    return intent
                    
        logger.info(
            "Intent Defaulted",
            extra={"structured_log": True, "stage": "IntentDetectionEngine", "intent": "Unknown"}
        )
        return "Unknown"
