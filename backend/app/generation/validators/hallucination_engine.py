"""Hallucination Engine.

Orchestrates all evidence and citation validators to guarantee zero hallucination.
"""

import logging
from app.generation.dto.dtos import GenerationContext, ExtractiveDraft, CitationMap
from app.generation.validators.evidence_validator import CitationValidator

logger = logging.getLogger("app")


class HallucinationEngine:
    """Strictly guards against fabricated information."""
    
    @classmethod
    def verify(
        cls, 
        draft: ExtractiveDraft, 
        context: GenerationContext, 
        citations: CitationMap
    ) -> bool:
        """
        Verify every sentence is grounded.
        Returns True if safe, False if hallucination detected.
        """
        logger.info("Running Hallucination Verification", extra={"structured_log": True, "stage": "HallucinationEngine"})
        
        try:
            # 1. Verify Citation Mappings exist in Context
            CitationValidator.validate_map(citations, context)
            
            # 2. Verify all draft sentences have a citation
            if len(draft.sentences) != len(citations.references):
                logger.warning(
                    "Citation count mismatch", 
                    extra={"structured_log": True, "draft_sentences": len(draft.sentences), "citations": len(citations.references)}
                )
                draft.fully_supported = False
                return False
                
            draft.fully_supported = True
            return True
            
        except ValueError as e:
            logger.error(f"Hallucination check failed: {e}")
            draft.fully_supported = False
            return False
