"""Document Understanding & Metadata Extraction.

Runs deterministic NLP analysis on the entire document before chunking.
Extracts Document Type, Topics, Entities, Keywords, Language, and Intent.
"""

import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger("app")


class DocumentUnderstandingEngine:
    """Extracts enterprise metadata deterministically from cleaned document text."""

    # Document type heuristic markers
    DOC_TYPES = {
        "Policy": [r"\bpolicy\b", r"\bcompliance\b", r"\bguidelines\b", r"\bhandbook\b"],
        "FAQ": [r"\bfaq\b", r"\bfrequently asked questions\b", r"\bq\s*&\s*a\b"],
        "Architecture": [r"\barchitecture\b", r"\bsystem design\b", r"\btechnical spec\b", r"\bmicroservices\b"],
        "Procedure": [r"\bprocedure\b", r"\bhow to\b", r"\bstep-by-step\b", r"\bworkflow\b"],
        "Report": [r"\breport\b", r"\banalysis\b", r"\bsummary\b", r"\bmetrics\b"],
    }

    # Common stop words for keyword extraction
    STOP_WORDS = {
        "the", "and", "or", "is", "in", "to", "of", "a", "for", "with", "as", "on", "by", "this",
        "that", "it", "are", "be", "an", "at", "from", "can", "will", "has", "have", "not",
        "we", "you", "they", "our", "your", "their", "which", "what", "how", "if", "but", "all"
    }

    @classmethod
    def extract_metadata(cls, pages: list[str], filename: str = "") -> dict[str, Any]:
        """Run full document understanding pipeline."""
        full_text = "\n\n".join(pages)
        text_lower = full_text.lower()
        
        metadata = {
            "document_type": cls._detect_document_type(text_lower, filename.lower()),
            "language": "en", # Defaulting to English for deterministic extraction
            "keywords": cls._extract_keywords(text_lower),
            "topics": cls._extract_topics(text_lower),
            "entities": cls._extract_entities(full_text),
            "contains_faq": bool(re.search(r"\bfaq\b|\bfrequently asked questions\b|\b[qQ]\s*&\s*[aA]\b", text_lower)),
            "contains_workflow": bool(re.search(r"\bworkflow\b|\bprocess flow\b|\bstep \d+\b", text_lower)),
            "contains_architecture": bool(re.search(r"\barchitecture\b|\bsystem design\b", text_lower)),
        }
        
        return metadata

    @classmethod
    def _detect_document_type(cls, text_lower: str, filename_lower: str) -> str:
        """Heuristically determine document type."""
        scores = Counter()
        
        for doc_type, patterns in cls.DOC_TYPES.items():
            for pattern in patterns:
                # Weight filename matches heavily
                if re.search(pattern, filename_lower):
                    scores[doc_type] += 5
                # Weight body matches
                matches = re.findall(pattern, text_lower)
                scores[doc_type] += len(matches)
                
        if not scores:
            return "General Document"
            
        return scores.most_common(1)[0][0]

    @classmethod
    def _extract_keywords(cls, text_lower: str, top_n: int = 10) -> list[str]:
        """Extract top N keywords excluding stop words."""
        words = re.findall(r"\b[a-z]{4,}\b", text_lower)
        filtered = [w for w in words if w not in cls.STOP_WORDS]
        counts = Counter(filtered)
        return [word for word, count in counts.most_common(top_n)]
        
    @classmethod
    def _extract_topics(cls, text_lower: str) -> list[str]:
        """Extract primary topics based on known enterprise terminology."""
        # This can be expanded with an enterprise ontology dictionary
        enterprise_topics = {
            "cloud": ["aws", "azure", "gcp", "cloud computing", "docker", "kubernetes"],
            "ai": ["artificial intelligence", "machine learning", "llm", "rag", "neural network"],
            "hr": ["leave", "payroll", "benefits", "reimbursement", "vacation"],
            "security": ["cybersecurity", "infosec", "iso27001", "authentication", "zero trust"]
        }
        
        detected = []
        for topic, terms in enterprise_topics.items():
            if any(term in text_lower for term in terms):
                detected.append(topic.capitalize())
                
        return detected if detected else ["General"]

    @classmethod
    def _extract_entities(cls, text: str) -> dict[str, list[str]]:
        """Extract named entities using spaCy if available, otherwise heuristic fallback."""
        entities = {
            "organizations": [],
            "people": [],
            "technologies": [],
            "dates": []
        }
        
        try:
            import spacy
            # Attempt to load small English model
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text[:100000]) # Limit for performance
            
            orgs = set()
            people = set()
            dates = set()
            
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    orgs.add(ent.text.strip())
                elif ent.label_ == "PERSON":
                    people.add(ent.text.strip())
                elif ent.label_ == "DATE":
                    dates.add(ent.text.strip())
                    
            entities["organizations"] = list(orgs)[:15]
            entities["people"] = list(people)[:15]
            entities["dates"] = list(dates)[:15]
            
        except Exception as e:
            logger.debug(f"spaCy NER not available or failed ({e}). Falling back to heuristics.")
            # Heuristic fallback for Tech (Capitalized words with numbers/acronyms)
            techs = set(re.findall(r"\b(?:[A-Z][a-z]*){1,}(?:[A-Z]|[0-9]+)\b", text))
            entities["technologies"] = list(techs)[:15]
            
        return entities
