"""Keyword Extractor Engine.

Extracts important keywords, acronyms, and product names using a TF-IDF 
or heuristic approach. Can be replaced with KeyBERT or YAKE in the future.
"""

import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger("app")

class BaseKeywordExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> list[str]:
        pass

class HeuristicKeywordExtractor(BaseKeywordExtractor):
    """A lightweight, deterministic keyword extractor."""
    
    STOP_WORDS = {
        "the", "and", "or", "is", "in", "to", "of", "a", "for", "with", "as", "on", "by", "this",
        "that", "it", "are", "be", "an", "at", "from", "can", "will", "has", "have", "not",
        "we", "you", "they", "our", "your", "their", "which", "what", "how", "if", "but", "all",
        "please", "tell", "me", "about", "show", "give", "provide", "details", "information"
    }

    def extract(self, text: str) -> list[str]:
        words = re.findall(r"\b[A-Za-z0-9\-]+\b", text.lower())
        keywords = []
        for w in words:
            if w not in self.STOP_WORDS and len(w) > 2:
                if w not in keywords:
                    keywords.append(w)
                    
        logger.debug(
            "Keyword Extraction Complete", 
            extra={"structured_log": True, "stage": "KeywordExtractor", "keywords": keywords}
        )
        return keywords
