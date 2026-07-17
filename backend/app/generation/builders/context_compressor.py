"""Algorithmic Context Compression.

Compresses the GenerationContext by removing duplicated sentences and overlapping 
chunks algorithmically (without invoking an LLM). Maintains deterministic ordering.
"""

import logging
from app.generation.dto.dtos import GenerationContext, GenerationEvidence

logger = logging.getLogger("app")


class ContextCompressor:
    """Removes redundancy from evidence prior to LLM submission."""
    
    @classmethod
    def compress(cls, context: GenerationContext) -> GenerationContext:
        """Apply algorithmic deduplication to the context."""
        
        if context.is_compressed:
            return context
            
        logger.info(
            "Starting Context Compression",
            extra={"structured_log": True, "stage": "ContextCompressor", "initial_tokens": context.total_tokens}
        )
        
        seen_sentences = set()
        compressed_evidence = []
        new_total_tokens = 0
        
        for evidence in context.evidence:
            # Simple sentence splitting (could be enhanced with spaCy/NLTK)
            sentences = [s.strip() for s in evidence.text.split(".") if len(s.strip()) > 10]
            unique_sentences = []
            
            for s in sentences:
                # Basic normalization for deduplication
                norm = s.lower().replace(" ", "")
                if norm not in seen_sentences:
                    seen_sentences.add(norm)
                    unique_sentences.append(s)
            
            if unique_sentences:
                compressed_text = ". ".join(unique_sentences) + "."
                # Approximate new token count
                ratio = len(compressed_text) / max(len(evidence.text), 1)
                new_tokens = int(evidence.token_count * ratio)
                
                compressed_evidence.append(
                    GenerationEvidence(
                        id=evidence.id,
                        text=compressed_text,
                        metadata=evidence.metadata,
                        source_chunk=evidence.source_chunk,
                        relevance_score=evidence.relevance_score,
                        token_count=new_tokens
                    )
                )
                new_total_tokens += new_tokens

        logger.info(
            "Context Compression Complete",
            extra={
                "structured_log": True, 
                "stage": "ContextCompressor",
                "old_tokens": context.total_tokens,
                "new_tokens": new_total_tokens,
                "ratio": round(new_total_tokens / max(context.total_tokens, 1), 2)
            }
        )
        
        return GenerationContext(
            evidence=compressed_evidence,
            total_tokens=new_total_tokens,
            is_compressed=True
        )
