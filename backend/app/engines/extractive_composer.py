"""Enterprise Extractive Composer.

Acts as a robust fallback answer generator that extracts the most relevant sentences
using Maximal Marginal Relevance (MMR) and formats them adaptively based on context.
"""

import re
from typing import Any, AsyncGenerator
from collections import defaultdict
from app.engines.rag_engine import AnswerGenerator

class ExtractiveComposer(AnswerGenerator):
    """Enterprise-grade extractive answer generator using MMR and Adaptive Formatting."""

    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        if not chunks:
            return "I couldn't find enough information in the uploaded documents."

        # 1. Clean query for relevance scoring
        query_words = {w.lower().strip("?,.!:;()\"'") for w in query.split()}
        filler_words = {
            "what", "is", "the", "for", "are", "but", "not", "you", "all", "any",
            "can", "had", "was", "how", "why", "when", "where", "who", "tell",
            "about", "details", "information", "do", "does", "me", "my", "your",
            "please", "explain", "describe", "show", "list", "give", "and", "or"
        }
        query_content_words = query_words - filler_words
        if not query_content_words:
            query_content_words = query_words

        # 2. Build unique citations key list
        unique_citations = []
        for c in chunks:
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            citation_key = (filename, page)
            if citation_key not in unique_citations:
                unique_citations.append(citation_key)

        # 3. Extract and score sentences
        extracted_sentences = []
        seen_sentences = set()

        for c in chunks:
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            citation_idx = unique_citations.index((filename, page)) + 1
            section = (c.get("section") or "").strip()

            text = c.get("text", "")
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean or len(s_clean) < 15:
                    continue
                s_norm = s_clean.lower()
                if s_norm in seen_sentences:
                    continue
                seen_sentences.add(s_norm)

                s_words = {w.lower().strip("?,.!:;()\"'") for w in s_clean.split()}
                overlap = s_words.intersection(query_content_words)
                score = len(overlap)

                heading = (c.get("heading") or "").lower()
                section_lower = section.lower()
                for qw in query_content_words:
                    if qw in heading or qw in section_lower:
                        score += 1

                extracted_sentences.append({
                    "text": s_clean,
                    "score": score,
                    "words": s_words,
                    "citation_idx": citation_idx,
                    "filename": filename,
                    "page": page,
                    "section": section
                })

        # 4. Maximal Marginal Relevance (MMR) Selection
        selected = []
        lambda_param = 0.7
        
        while len(selected) < 6 and extracted_sentences:
            best_idx = -1
            best_mmr_score = -float('inf')
            
            for i, candidate in enumerate(extracted_sentences):
                max_similarity = 0.0
                for sel in selected:
                    intersection = len(candidate["words"].intersection(sel["words"]))
                    union = len(candidate["words"].union(sel["words"]))
                    if union > 0:
                        sim = intersection / union
                        if sim > max_similarity:
                            max_similarity = sim
                            
                mmr_score = (lambda_param * candidate["score"]) - ((1 - lambda_param) * max_similarity * 10)
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = i
                    
            if best_idx != -1:
                selected.append(extracted_sentences.pop(best_idx))
            else:
                break

        if not selected:
            c = chunks[0]
            text_preview = c.get("text", "")[:500]
            return f"{text_preview}...\n\n**Sources:**\n{c.get('filename')} — Page {c.get('page_number', 1)}"

        # 5. Entity & Section Grouping (No formatting here)
        grouped_by_section = defaultdict(list)
        for s in selected:
            group_key = s["section"] if s["section"] else "General"
            grouped_by_section[group_key].append(s)

        # Build citations
        citations = [f"{fn} — Page {pg}" for (fn, pg) in unique_citations]

        # Return structured data for Formatter
        return {
            "grouped_by_section": grouped_by_section,
            "citations": citations
        }
