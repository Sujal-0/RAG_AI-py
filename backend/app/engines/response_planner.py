"""Response Planner Engine.

Analyzes the query intent, structural cues, and extracted evidence to generate
a versioned ResponsePlan object that dictates exactly how the LLM or Extractive Composer
should format its output (e.g., Markdown tables, numbered steps, concise paragraphs).
"""

import re
from dataclasses import dataclass
from typing import Any, List, Dict, Optional

@dataclass
class ResponsePlan:
    version: str = "response_plan_v2"
    format_type: str = "Paragraph"
    structure_guidelines: str = ""
    target_length: str = "Short"
    requires_citations: bool = True
    requires_llm_enhancement: bool = False

    def to_dict(self):
        return {
            "version": self.version,
            "format_type": self.format_type,
            "structure_guidelines": self.structure_guidelines,
            "target_length": self.target_length,
            "requires_citations": self.requires_citations,
            "requires_llm_enhancement": self.requires_llm_enhancement
        }

class ResponsePlanner:
    """Decides HOW the response should be generated (format, length, structure)."""

    def __init__(self):
        self.version = "response_plan_v2"

    def plan_response(self, query: str, chunks: List[Dict[str, Any]], intent: Optional[str] = None, confidence: float = 0.0, extractive_draft: Any = None) -> ResponsePlan:
        """Analyze query and context to construct a ResponsePlan."""
        q_lower = query.lower()
        
        # Default Plan
        plan = ResponsePlan(
            version=self.version,
            format_type="Paragraph",
            structure_guidelines="Respond in 2-3 concise paragraphs. Merge overlapping information.",
            target_length="Medium",
            requires_citations=True,
            requires_llm_enhancement=False
        )

        # 1. Determine requires_llm_enhancement
        # Only true for: Summarization, Rewriting, Simplification, Long explanation, Tone improvement, Creative writing
        enhancement_triggers = [
            "summarize", "summary", "rewrite", "simplify", "explain in detail",
            "long explanation", "improve tone", "creative", "write an email",
            "draft a message"
        ]
        if any(trigger in q_lower for trigger in enhancement_triggers):
            plan.requires_llm_enhancement = True
            
        # Confidence-based bypass (Rule #4)
        if confidence >= 0.80:
            # High confidence facts bypass LLM regardless, unless explicitly asking for rewrite
            pass

        # 2. Determine format_type
        # Detect comparison
        if "compare" in q_lower or "difference between" in q_lower or "vs" in q_lower:
            plan.format_type = "Markdown table"
            plan.structure_guidelines = "Use a Markdown table to compare the requested entities side-by-side. Include an introductory sentence."
            plan.target_length = "Medium"
            
        # Detect steps/procedures
        elif "how to" in q_lower or "steps" in q_lower or "guide" in q_lower or "process" in q_lower:
            plan.format_type = "Numbered steps"
            plan.structure_guidelines = "Use a numbered list to outline the process sequentially. Keep each step actionable."
            plan.target_length = "Medium"
            
        # Detect list request
        elif "list" in q_lower or "what are the" in q_lower or "features" in q_lower or "benefits" in q_lower:
            plan.format_type = "Bullet list"
            plan.structure_guidelines = "Use a bulleted list to enumerate the items clearly."
            plan.target_length = "Medium"
            
        # Detect FAQ
        elif "faq" in q_lower or "frequently asked" in q_lower:
            plan.format_type = "FAQ"
            plan.structure_guidelines = "Format as a Q&A."
            
        # Detect Policy
        elif "policy" in q_lower or "rules" in q_lower or "handbook" in q_lower:
            plan.format_type = "Policy"
            plan.structure_guidelines = "Format as Policy Sections."

        return plan
