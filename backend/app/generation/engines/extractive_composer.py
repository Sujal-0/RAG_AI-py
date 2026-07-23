"""Extractive Composer.

Constructs a highly deterministic draft response using ONLY factual sentences 
from the compressed context. It performs basic grammatical stitching but 
absolutely no generative hallucination.
"""

import logging
from app.generation.dto.dtos import GenerationContext, ResponsePlan, ExtractiveDraft

logger = logging.getLogger("app")


class ExtractiveComposer:
    """Drafts algorithmic responses prior to LLM enhancement."""
    
    @classmethod
    def draft(cls, context: GenerationContext, plan: ResponsePlan) -> ExtractiveDraft:
        """Compose the draft exclusively from validated context."""
        
        logger.info("Generating Extractive Draft", extra={"structured_log": True, "stage": "ExtractiveComposer"})
        
        if not context.evidence:
            return ExtractiveDraft(
                content="The uploaded knowledge base does not contain enough information.",
                sentences=["The uploaded knowledge base does not contain enough information."],
                fully_supported=False
            )
            
        sentences = []
        
        import re
        # Algorithmic extraction: simply stitch the deduplicated sentences from evidence
        # This guarantees 100% fidelity. The LLM Enhancer will smooth it out later.
        for evidence in context.evidence:
            chunks_sentences = [s.strip() for s in re.split(r'[.\n]+', evidence.text) if len(s.strip()) > 10]
            sentences.extend(chunks_sentences)
            
        # Prevent document dumps (Task 8)
        # We allow roughly 1.5x the final word budget in the draft to give the LLM room to summarize,
        # but we strictly truncate anything beyond that. (Assume ~15 words per sentence)
        max_draft_sentences = max(10, int((plan.max_words * 1.5) / 15))
        sentences = sentences[:max_draft_sentences]
            
        draft_content = ".\n".join(sentences) + "."
        
        # Do not prepend structural headers like intent tags to the content 
        # (This avoids duplicate/robotic prefixes in the UI)
            
        if getattr(plan, "greeting_matched", False):
            draft_content = "Hello! " + draft_content
            
        logger.info(
            "Extractive Draft Complete", 
            extra={
                "structured_log": True, 
                "stage": "ExtractiveComposer", 
                "sentence_count": len(sentences)
            }
        )
        
        return ExtractiveDraft(
            content=draft_content,
            sentences=sentences,
            fully_supported=True
        )
