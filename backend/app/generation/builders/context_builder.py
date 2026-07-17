"""Context Builder Engine.

Transforms flat RetrievalResult evidence into a structured GenerationContext.
Preserves original document ordering and ensures table/workflow boundaries are respected.
"""

import logging
from typing import Any

from app.generation.dto.dtos import GenerationContext, GenerationEvidence

logger = logging.getLogger("app")


class ContextBuilder:
    """Constructs the foundational Generation Context from retrieved evidence."""
    
    @classmethod
    def build(cls, raw_evidence: list[dict[str, Any]]) -> GenerationContext:
        """Map raw dictionary chunks into strongly typed GenerationEvidence."""
        
        evidence_list = []
        total_tokens = 0
        
        # Sort evidence by document and chunk_index to preserve natural reading order
        # Ensure we don't crash if metadata is missing
        sorted_raw = sorted(
            raw_evidence, 
            key=lambda x: (
                x["chunk"].chunk_metadata.get("document_id", ""),
                x["chunk"].chunk_index
            )
        )
        
        for item in sorted_raw:
            chunk = item["chunk"]
            
            evidence = GenerationEvidence(
                id=str(chunk.id),
                text=chunk.text,
                metadata=chunk.chunk_metadata,
                source_chunk=chunk,
                relevance_score=item.get("hybrid_score", item.get("rerank_score", 0.0)),
                token_count=chunk.token_count
            )
            
            evidence_list.append(evidence)
            total_tokens += chunk.token_count
            
        logger.info(
            "Context Built",
            extra={
                "structured_log": True, 
                "stage": "ContextBuilder", 
                "evidence_count": len(evidence_list),
                "total_tokens": total_tokens
            }
        )
            
        return GenerationContext(
            evidence=evidence_list,
            total_tokens=total_tokens,
            is_compressed=False
        )
