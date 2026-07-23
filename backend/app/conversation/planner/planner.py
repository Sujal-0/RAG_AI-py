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
        
        decision_result = DecisionEngine.classify(query)
        intent = decision_result["intent"]
        processed_query = decision_result.get("processed_query", query)
        
        # Fast paths that don't need RAG
        skip_retrieval = intent in ["Greeting", "Goodbye", "Thanks", "ConversationControl", "Clarification", "AssistantIdentity", "Gibberish", "SmallTalk", "Empty", "Help"]
        
        plan = ExecutionPlan(
            intent=intent,
            processed_query=processed_query,
            confidence=decision_result["confidence"],
            fastpath=skip_retrieval,
            needs_retrieval=not skip_retrieval,
            needs_generation=not skip_retrieval,
            response_template="",
            max_chunks=3,
            token_budget=4096,
            skip_retrieval=skip_retrieval,
            need_clarification=False,
            need_cache=settings.conversation.enable_caching,
            need_multi_query=settings.conversation.enable_multi_query,
            need_streaming=settings.conversation.enable_streaming,
            need_citation=not skip_retrieval,
            intent_confidence=decision_result["confidence"],
            greeting_matched=decision_result.get("greeting_matched", False)
        )
        
        if intent == "Empty":
            plan.clarification_message = "Please enter a question."
            plan.needs_generation = False
            
        elif intent == "Greeting":
            plan.clarification_message = "Hello! How can I assist you with the Mobiloitte AI Platform today?"
            plan.needs_generation = False
            
        elif intent == "Thanks":
            plan.clarification_message = "You're very welcome! Let me know if you need anything else."
            plan.needs_generation = False
            
        elif intent == "Goodbye":
            plan.clarification_message = "Goodbye! Have a great day."
            plan.needs_generation = False
            
        elif intent == "Clarification":
            plan.clarification_message = "Could you please provide a bit more detail so I can help you better?"
            plan.needs_generation = False
            
        elif intent == "AssistantIdentity":
            plan.clarification_message = "I am the Mobiloitte AI Platform Assistant. I'm here to help you navigate our company policies, technology stack, structure, and internal knowledge. How can I help?"
            plan.needs_generation = False
            
        elif intent == "Gibberish":
            if decision_result.get("greeting_matched"):
                plan.clarification_message = "Hello! I couldn't understand your question. Could you please rephrase?"
            else:
                plan.clarification_message = "I couldn't understand your question. Could you please rephrase?"
            plan.needs_generation = False

        elif intent == "Help":
            plan.clarification_message = "I can answer questions about Mobiloitte's internal knowledge base. Just ask me anything!"
            plan.needs_generation = False

        elif intent == "SmallTalk":
            plan.clarification_message = "I'm doing well, thank you! How can I help you with our company information today?"
            plan.needs_generation = False
            
        logger.info("Execution Plan Complete", extra={"structured_log": True, "stage": "Planner", "plan": plan.__dict__})
        return plan
