"""Response Planner.

Translates the Retrieval Intent into a structured ResponsePlan detailing the 
expected formatting (Tables, Workflows, Comparisons) and layout requirements.
"""

import logging
from app.generation.dto.dtos import ResponsePlan

logger = logging.getLogger("app")

class ResponsePlanner:
    """Determines the architectural layout and execution limits of the final response."""
    
    @classmethod
    def plan(cls, intent: str, greeting_matched: bool = False) -> ResponsePlan:
        """Map intent to a structural blueprint and constraints."""
        
        logger.info(f"Planning response for intent: {intent}", extra={"structured_log": True, "stage": "ResponsePlanner"})
        
        # Safe Defaults (KnowledgeQuery / Unknown)
        format_type = "paragraph"
        sections = ["Answer"]
        token_budget = 1000
        max_words = 180
        max_chunks = 5
        temperature = 0.2
        requires_citations = True
        stream = True
        compression_level = "low"
        allow_markdown = True
        requires_safety_disclaimer = False
        
        if intent in ["Greeting", "Thanks", "Help", "Goodbye"]:
            format_type = "short_answer"
            token_budget = 0
            max_words = 25
            max_chunks = 0
            temperature = 0.7
            requires_citations = False
            stream = False
            allow_markdown = False
            
        elif intent == "Definition":
            format_type = "definition"
            token_budget = 350
            max_words = 120
            max_chunks = 2
            temperature = 0.1
            
        elif intent == "Summary":
            format_type = "paragraph"
            sections = ["Executive Summary"]
            token_budget = 700
            max_words = 180
            max_chunks = 4
            temperature = 0.2
            compression_level = "high"
            
        elif intent == "Timeline":
            format_type = "timeline"
            sections = ["Chronology"]
            token_budget = 800
            max_chunks = 5
            compression_level = "medium"
            allow_markdown = True
            
        elif intent == "Comparison":
            format_type = "comparison_table"
            sections = ["Comparison Table", "Summary"]
            token_budget = 1000
            max_words = 250
            max_chunks = 6
            temperature = 0.1
            allow_markdown = True
            
        elif intent == "Table":
            format_type = "Markdown Table"
            sections = ["Table"]
            token_budget = 1000
            max_chunks = 6
            allow_markdown = True
            
        elif intent in ["List", "Advantages", "Disadvantages"]:
            format_type = "bullet_list"
            sections = ["Key Points"]
            token_budget = 800
            max_chunks = 5 if intent == "List" else 4
            
        elif intent == "Steps":
            format_type = "numbered_steps"
            sections = ["Procedure"]
            token_budget = 800
            max_chunks = 5
            
        elif intent == "FAQ":
            format_type = "faq"
            sections = ["Questions and Answers"]
            token_budget = 800
            max_chunks = 4
            
        elif intent == "Explanation":
            format_type = "long_answer"
            sections = ["Explanation", "Details"]
            token_budget = 1200
            max_chunks = 5
            
        elif intent == "ConversationFollowUp":
            format_type = "paragraph"
            token_budget = 500
            max_chunks = 3
            compression_level = "high"
            
        elif intent == "Clarification":
            format_type = "short_answer"
            token_budget = 200
            max_chunks = 1
            requires_citations = False
            
        elif intent in ["Policy", "Security"]: # Legacy support mapping
            requires_safety_disclaimer = True
            
        if intent == "AssistantIdentity":
            max_words = 40
            
        plan = ResponsePlan(
            intent=intent,
            format_type=format_type,
            sections=sections,
            token_budget=token_budget,
            max_words=max_words,
            max_chunks=max_chunks,
            temperature=temperature,
            requires_citations=requires_citations,
            stream=stream,
            compression_level=compression_level,
            allow_markdown=allow_markdown,
            requires_safety_disclaimer=requires_safety_disclaimer,
            greeting_matched=greeting_matched
        )
        
        logger.debug("Response Plan generated", extra={"plan": plan.__dict__})
        return plan
