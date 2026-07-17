"""Conversation Planner.

Evaluates the classified intent from the Decision Engine and the current 
Conversation Session to construct a deterministic ExecutionPlan.
"""

import logging
from app.core.settings import settings
from app.conversation.dto.dtos import ExecutionPlan, ConversationSession
from app.conversation.planner.decision_engine import DecisionEngine

logger = logging.getLogger("app")


class ConversationPlanner:
    """Produces the execution plan without running any side-effects."""
    
    @classmethod
    def plan(cls, query: str, session: ConversationSession) -> ExecutionPlan:
        logger.info("Generating Execution Plan", extra={"structured_log": True, "stage": "Planner"})
        
        classification, skip_retrieval = DecisionEngine.classify(query)
        
        plan = ExecutionPlan(
            skip_retrieval=skip_retrieval,
            need_clarification=False,
            need_cache=settings.conversation.enable_caching,
            need_multi_query=settings.conversation.enable_multi_query,
            need_generation=True,
            need_streaming=settings.conversation.enable_streaming,
            need_citation=not skip_retrieval,
        )
        
        if classification == "Greeting":
            plan.clarification_message = "Hello! How can I assist you with the Mobiloitte AI Platform today?"
            plan.need_generation = False # We can directly serve the static response
            
        elif classification == "Small Talk":
            plan.clarification_message = "You're very welcome! Let me know if you need anything else."
            plan.need_generation = False
            
        elif classification == "Conversation Control":
            plan.clarification_message = "I have acknowledged your command."
            plan.need_generation = False
            
        logger.info("Execution Plan Complete", extra={"structured_log": True, "stage": "Planner", "plan": plan.__dict__})
        return plan
