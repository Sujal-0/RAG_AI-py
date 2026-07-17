"""Context Window Manager.

Enforces LLM token budgets and limits on the GenerationContext.
Uses greedy prioritization (highest relevance first) while keeping 
neighboring blocks intact when possible.
"""

import logging
from app.core.settings import settings
from app.generation.dto.dtos import GenerationContext

logger = logging.getLogger("app")


class ContextWindowManager:
    """Manages LLM token constraints prior to compression."""
    
    @classmethod
    def select(cls, context: GenerationContext) -> GenerationContext:
        """Trims context to fit within the configured maximum input tokens."""
        
        max_tokens = settings.generation.max_input_tokens
        
        if context.total_tokens <= max_tokens:
            logger.debug("Context fits within window without truncation.")
            return context
            
        logger.warning(
            f"Context exceeds token limit ({context.total_tokens} > {max_tokens}). Truncating.",
            extra={"structured_log": True, "stage": "ContextWindowManager"}
        )
        
        # Prioritize by relevance score
        prioritized = sorted(context.evidence, key=lambda x: x.relevance_score, reverse=True)
        
        accepted_evidence = []
        current_tokens = 0
        
        for evidence in prioritized:
            if current_tokens + evidence.token_count <= max_tokens:
                accepted_evidence.append(evidence)
                current_tokens += evidence.token_count
            else:
                break
                
        # Re-sort accepted evidence back into reading order
        accepted_evidence.sort(
            key=lambda x: (
                x.metadata.get("document_id", ""),
                x.source_chunk.chunk_index
            )
        )
        
        logger.info(
            "Context Window Applied",
            extra={
                "structured_log": True, 
                "stage": "ContextWindowManager", 
                "original_count": len(context.evidence),
                "new_count": len(accepted_evidence),
                "new_tokens": current_tokens
            }
        )
        
        return GenerationContext(
            evidence=accepted_evidence,
            total_tokens=current_tokens,
            is_compressed=False
        )
