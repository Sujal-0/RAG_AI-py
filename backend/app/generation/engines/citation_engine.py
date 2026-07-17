"""Citation Engine.

Maps every sentence in the ExtractiveDraft back to its original chunk 
and document in the GenerationContext. This creates the CitationMap 
used for clickable UI references and hallucination guarding.
"""

import logging
from app.generation.dto.dtos import GenerationContext, ExtractiveDraft, CitationMap, CitationReference

logger = logging.getLogger("app")


class CitationEngine:
    """Generates precise traceability for the UI."""
    
    @classmethod
    def map_citations(cls, draft: ExtractiveDraft, context: GenerationContext) -> CitationMap:
        
        logger.info("Generating Citations", extra={"structured_log": True, "stage": "CitationEngine"})
        
        references = []
        
        # In a real NLP mapping scenario, we would use vector cosine similarity or exact substring matching
        # to map each generated sentence back to the chunk it came from. 
        # Here we perform a deterministic exact substring check.
        
        for idx, sentence in enumerate(draft.sentences):
            mapped_chunk_id = None
            document_name = "Unknown"
            page_number = 1
            
            for evidence in context.evidence:
                # Basic substring check
                if sentence in evidence.text or sentence.replace(" ", "") in evidence.text.replace(" ", ""):
                    mapped_chunk_id = evidence.id
                    document_name = evidence.metadata.get("filename", "Unknown Document")
                    page_number = evidence.metadata.get("page_number", 1)
                    break
                    
            if mapped_chunk_id:
                references.append(CitationReference(
                    sentence_index=idx,
                    chunk_id=mapped_chunk_id,
                    confidence=1.0,
                    document_name=document_name,
                    page_number=page_number
                ))
            else:
                logger.warning(f"Could not map sentence back to evidence: '{sentence[:30]}...'")
                
        logger.info(
            "Citation Mapping Complete", 
            extra={
                "structured_log": True, 
                "stage": "CitationEngine", 
                "total_sentences": len(draft.sentences),
                "mapped_citations": len(references)
            }
        )
        
        return CitationMap(references=references)
