"""Response Planner.

Translates the Retrieval Intent into a structured ResponsePlan detailing the 
expected formatting (Tables, Workflows, Comparisons) and layout requirements.
"""

import logging
from app.generation.dto.dtos import ResponsePlan

logger = logging.getLogger("app")


class ResponsePlanner:
    """Determines the architectural layout of the final response."""
    
    @classmethod
    def plan(cls, intent: str) -> ResponsePlan:
        """Map intent to a structural blueprint."""
        
        logger.info(f"Planning response for intent: {intent}", extra={"structured_log": True, "stage": "ResponsePlanner"})
        
        # Defaults
        format_type = "Standard"
        sections = ["Answer"]
        requires_citations = True
        
        if intent == "Comparison":
            format_type = "Markdown Table"
            sections = ["Comparison Table", "Summary"]
        elif intent == "Procedure" or intent == "Workflow":
            format_type = "Step-by-Step"
            sections = ["Prerequisites", "Steps", "Verification"]
        elif intent == "Architecture":
            format_type = "Nested Sections"
            sections = ["Overview", "Components", "Data Flow"]
        elif intent == "FAQ":
            format_type = "Bullet List"
        
        plan = ResponsePlan(
            format_type=format_type,
            sections=sections,
            requires_citations=requires_citations,
            requires_safety_disclaimer=(intent in ["Policy", "Security"])
        )
        
        logger.debug("Response Plan generated", extra={"plan": plan.__dict__})
        return plan
