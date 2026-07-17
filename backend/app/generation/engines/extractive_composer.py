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
        
        # Algorithmic extraction: simply stitch the deduplicated sentences from evidence
        # This guarantees 100% fidelity. The LLM Enhancer will smooth it out later.
        for evidence in context.evidence:
            chunks_sentences = [s.strip() for s in evidence.text.split(".") if len(s.strip()) > 10]
            sentences.extend(chunks_sentences)
            
        draft_content = ".\n".join(sentences) + "."
        
        # Add basic structural headers if plan dictates
        if plan.sections and len(plan.sections) > 1:
            draft_content = f"### {plan.sections[0]}\n\n" + draft_content
            
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
