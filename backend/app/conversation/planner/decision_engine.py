"""Decision Engine for the Conversation Intelligence Platform.

Classifies queries instantaneously to skip Retrieval/Generation pipelines 
whenever possible (e.g. for greetings or small talk).
"""

import logging
from typing import Tuple

logger = logging.getLogger("app")


class DecisionEngine:
    """Classifies user input into deterministic conversation intents."""
    
    @classmethod
    def classify(cls, query: str) -> Tuple[str, bool]:
        """
        Classifies the query and determines if Retrieval can be skipped.
        Returns: (classification, skip_retrieval)
        """
        norm = query.lower().strip()
        
        # Fast deterministic checks to avoid expensive NLP/LLM layers
        greetings = {"hi", "hello", "hey", "good morning", "good evening"}
        gratitude = {"thanks", "thank you", "thx", "appreciate it"}
        control = {"continue", "stop", "cancel", "clear context", "reset"}
        
        if norm in greetings:
            logger.info("DecisionEngine: Detected Greeting", extra={"structured_log": True, "stage": "DecisionEngine"})
            return "Greeting", True
            
        if norm in gratitude:
            logger.info("DecisionEngine: Detected Small Talk (Gratitude)", extra={"structured_log": True, "stage": "DecisionEngine"})
            return "Small Talk", True
            
        if norm in control:
            logger.info("DecisionEngine: Detected Conversation Control", extra={"structured_log": True, "stage": "DecisionEngine"})
            return "Conversation Control", True
            
        # If it's short, it might be a follow-up or clarification
        if len(norm.split()) <= 3:
            logger.info("DecisionEngine: Detected Potential Follow-up", extra={"structured_log": True, "stage": "DecisionEngine"})
            return "Follow-up", False
            
        logger.info("DecisionEngine: Detected Knowledge Query", extra={"structured_log": True, "stage": "DecisionEngine"})
        return "Knowledge Query", False
