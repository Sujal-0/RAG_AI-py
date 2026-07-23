"""Prompt Builder.

Responsibility is strictly restricted to template construction.
Assembles the Extractive Draft, System Rules, and Response Plan into a PromptBundle.
The LLMEnhancer will use this bundle solely for language polishing.
"""

import logging
from app.generation.dto.dtos import ExtractiveDraft, ResponsePlan, PromptBundle

logger = logging.getLogger("app")


class PromptBuilder:
    """Creates deterministic prompts for the LLM Enhancer."""
    
    SYSTEM_PROMPT = """You are an Enterprise AI Response Enhancer.
Your ONLY job is to take the provided Extractive Draft and polish the grammar, readability, and flow.
DO NOT ADD ANY NEW FACTS.
DO NOT HALLUCINATE.
DO NOT REMOVE CITATIONS.
NEVER include entire document chunks, full texts, or full paragraphs. Only use the selected evidence in the draft.
You must strictly follow the provided Formatting Instructions."""

    @classmethod
    def build(cls, draft: ExtractiveDraft, plan: ResponsePlan) -> PromptBundle:
        
        logger.info("Building Prompt Bundle", extra={"structured_log": True, "stage": "PromptBuilder"})
        
        formatting_rules = f"Format the output as a {plan.format_type}.\n"
        if plan.sections:
            formatting_rules += f"Include the following sections: {', '.join(plan.sections)}.\n"
            
        formatting_rules += f"STRICT CONSTRAINT: The absolute maximum length is {plan.max_words} words. Do not exceed this limit.\n"
        
        if getattr(plan, "greeting_matched", False):
            formatting_rules += "The user started their request with a greeting. You MUST start your response with a polite greeting (e.g., 'Hello!', 'Hi there!').\n"
            
        return PromptBundle(
            system_prompt=cls.SYSTEM_PROMPT,
            user_prompt="Please polish this extractive draft into a professional enterprise response.",
            context_text=draft.content,
            formatting_instructions=formatting_rules
        )
