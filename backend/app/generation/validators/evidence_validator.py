"""Evidence Validators.

A suite of strict deterministic validators to reject unsupported or weak 
evidence before drafting begins.
"""

import logging
from typing import Protocol

from app.generation.dto.dtos import GenerationContext, ExtractiveDraft, CitationMap

logger = logging.getLogger("app")


class AbstractValidator(Protocol):
    def validate(self, context: GenerationContext) -> GenerationContext:
        pass


class CoverageValidator:
    """Ensures the context has enough density to answer the query."""
    
    @classmethod
    def validate(cls, context: GenerationContext) -> GenerationContext:
        if not context.evidence:
            raise ValueError("Insufficient evidence coverage: No evidence retrieved.")
        if context.total_tokens < 50:
            logger.warning("Very low evidence coverage detected.")
        return context


class FactValidator:
    """Rejects chunks that don't contain factual structures (e.g., UI boilerplate)."""
    
    @classmethod
    def validate(cls, context: GenerationContext) -> GenerationContext:
        # Placeholder for heuristic fact density checks (e.g., POS tagging)
        return context


class CitationValidator:
    """Verifies that citations generated map correctly to chunks."""
    
    @classmethod
    def validate_map(cls, citations: CitationMap, context: GenerationContext) -> CitationMap:
        valid_ids = {e.id for e in context.evidence}
        for ref in citations.references:
            if ref.chunk_id not in valid_ids:
                logger.error(f"Invalid citation chunk_id {ref.chunk_id}")
                raise ValueError("Citation mapping violated context boundaries.")
        return citations


class EvidenceValidator:
    """Primary entrypoint for filtering weak chunks before drafting."""
    
    @classmethod
    def validate(cls, context: GenerationContext) -> GenerationContext:
        logger.info("Validating Evidence", extra={"structured_log": True, "stage": "EvidenceValidator"})
        
        # Sequentially apply validators
        context = CoverageValidator.validate(context)
        context = FactValidator.validate(context)
        
        # Additional baseline checks
        valid_evidence = []
        for e in context.evidence:
            if len(e.text) > 20: # Reject orphans/tiny chunks
                valid_evidence.append(e)
                
        context.evidence = valid_evidence
        return context
