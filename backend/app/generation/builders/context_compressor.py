"""Algorithmic Context Compression.

Compresses the GenerationContext by removing duplicated sentences and overlapping 
chunks algorithmically (without invoking an LLM). Maintains deterministic ordering.
"""

import logging
import re
from app.generation.dto.dtos import GenerationContext, GenerationEvidence, ResponsePlan

logger = logging.getLogger("app")

class ContextCompressor:
    """Removes redundancy and enforces ResponsePlan limits prior to LLM submission."""
    
    @classmethod
    def compress(cls, context: GenerationContext, plan: ResponsePlan, query: str = "") -> GenerationContext:
        """Apply algorithmic deduplication and intent filtering to the context."""
        
        if context.is_compressed:
            return context
            
        logger.info(
            f"Starting Context Compression for {plan.intent}",
            extra={"structured_log": True, "stage": "ContextCompressor", "initial_tokens": context.total_tokens}
        )
        
        original_tokens = context.total_tokens
        seen_sentences = set()
        compressed_evidence = []
        new_total_tokens = 0
        chunks_removed = 0
        sentences_removed = 0
        
        # 1. Enforce Chunk Budget
        valid_evidence = context.evidence[:plan.max_chunks]
        chunks_removed = len(context.evidence) - len(valid_evidence)
        
        # 2. Query Filtering (Task 9: Strict Context Filtering)
        query_words = set(re.findall(r'\b\w+\b', query.lower())) - {"what", "is", "the", "a", "an", "how", "where", "who", "when", "why", "are", "do", "does", "in", "of", "and", "or", "for", "to", "with"}
        
        # 3. Intent Filtering Patterns
        # Definition: keep "is a", "refers to", "means"
        # Summary: keep "summary", "conclusion", "overall", etc.
        # Timeline: keep dates (regex for years or months)
        # Comparison: keep "vs", "difference", "advantage", "both"
        intent_regex = None
        if plan.compression_level in ["medium", "high"]:
            if plan.intent == "Definition":
                intent_regex = re.compile(r'\b(is a|refers to|means|defined as|represents)\b', re.IGNORECASE)
            elif plan.intent == "Timeline":
                intent_regex = re.compile(r'\b(19\d{2}|20\d{2}|january|february|march|april|may|june|july|august|september|october|november|december)\b', re.IGNORECASE)
            elif plan.intent == "Comparison":
                intent_regex = re.compile(r'\b(vs|versus|difference|compared to|while|however|both|advantages?|disadvantages?)\b', re.IGNORECASE)
            elif plan.intent in ["Steps", "Procedure"]:
                intent_regex = re.compile(r'\b(step|first|then|finally|click|use|open|run|execute)\b', re.IGNORECASE)
            elif plan.intent == "FAQ":
                intent_regex = re.compile(r'(\?|\b(how|what|why|when|where)\b)', re.IGNORECASE)

        for evidence in valid_evidence:
            # Simple sentence splitting, keeping the delimiter.
            # Avoid splitting on decimals or abbreviations if possible, but basic split is fine.
            raw_sentences = [s.strip() + "." for s in evidence.text.split(".") if len(s.strip()) > 5]
            unique_sentences = []
            
            for s in raw_sentences:
                # Basic noise removal (page numbers, headers, table separators)
                if re.match(r'^page \d+$', s.lower().replace(".", "")): 
                    sentences_removed += 1
                    continue
                if "|" in s and "---" in s: # Table separator
                    sentences_removed += 1
                    continue
                    
                norm = s.lower().replace(" ", "").replace(".", "")
                
                # Duplicate removal
                if norm in seen_sentences:
                    sentences_removed += 1
                    continue
                    
                # Strict Query Filtering (Task 9)
                if query_words:
                    s_words = set(re.findall(r'\b\w+\b', s.lower()))
                    # If sentence has NO overlap with query keywords, and it's short, discard it
                    if not (s_words & query_words) and len(s_words) < 12:
                        sentences_removed += 1
                        continue

                # Intent-Aware Filtering for High Compression
                if intent_regex and plan.compression_level == "high":
                    # Keep if it matches intent regex OR if it's very long (maybe important)
                    if not intent_regex.search(s) and len(s.split()) < 15:
                        sentences_removed += 1
                        continue
                        
                seen_sentences.add(norm)
                unique_sentences.append(s)
            
            if unique_sentences:
                compressed_text = " ".join(unique_sentences)
                
                # Approximate new token count based on character ratio
                ratio = len(compressed_text) / max(len(evidence.text), 1)
                new_tokens = int(evidence.token_count * ratio)
                
                # Enforce Token Budget
                if new_total_tokens + new_tokens > plan.token_budget:
                    chunks_removed += 1
                    continue # Skip this entire chunk if it blows the budget
                    
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
            else:
                chunks_removed += 1

        logger.info(
            "Context Compression Complete",
            extra={
                "structured_log": True, 
                "stage": "ContextCompressor",
                "old_tokens": original_tokens,
                "new_tokens": new_total_tokens,
                "ratio": round(new_total_tokens / max(original_tokens, 1), 2)
            }
        )
        
        return GenerationContext(
            evidence=compressed_evidence,
            total_tokens=new_total_tokens,
            is_compressed=True,
            original_tokens=original_tokens,
            chunks_removed=chunks_removed,
            sentences_removed=sentences_removed
        )
