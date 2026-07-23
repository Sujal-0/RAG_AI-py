"""Query Analyzer Engine.

Responsible for normalizing user queries, detecting language, extracting abbreviations,
identifying the question type, and setting response expectations. Does NOT extract
keywords or entities (delegated to separate services).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("app")


@dataclass
class NormalizedQuery:
    """The canonical object passed through the retrieval pipeline."""
    original_text: str
    normalized_text: str
    language: str
    question_type: str
    response_expectation: str
    abbreviations: list[str] = field(default_factory=list)


class QueryAnalyzer:
    """Normalizes and analyzes the structure of user queries."""

    # Common English interrogatives
    QUESTION_TYPES = {
        "what": r"\bwhat\b",
        "who": r"\bwho\b",
        "where": r"\bwhere\b",
        "when": r"\bwhen\b",
        "why": r"\bwhy\b",
        "how": r"\bhow\b",
        "can": r"\bcan\b|\bcould\b",
        "is": r"\bis\b|\bare\b|\bdoes\b|\bdo\b"
    }

    @classmethod
    def analyze(cls, query: str) -> NormalizedQuery:
        """Run the query analysis pipeline."""
        normalized = cls._normalize(query)
        lang = cls._detect_language(normalized)
        q_type = cls._detect_question_type(normalized)
        expectation = cls._detect_response_expectation(normalized)
        abbrevs = cls._extract_abbreviations(query)

        logger.info(
            "Query Analysis Complete",
            extra={
                "structured_log": True,
                "stage": "QueryAnalyzer",
                "normalized": normalized,
                "q_type": q_type,
                "expectation": expectation,
            }
        )

        return NormalizedQuery(
            original_text=query,
            normalized_text=normalized,
            language=lang,
            question_type=q_type,
            response_expectation=expectation,
            abbreviations=abbrevs
        )

    @classmethod
    def _normalize(cls, text: str) -> str:
        """Remove excess noise and normalize spacing/punctuation."""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = text.replace("’", "'").replace("‘", "'")
        # Remove trailing question marks for cleaner downstream matching
        text = text.rstrip("?")
        
        # Normalize repetitive characters in common greetings (Task 2)
        text = re.sub(r"\b(h)(i+)\b", "hi", text)         # hii, hiii -> hi
        text = re.sub(r"\b(h)(e+)(y+)\b", "hey", text)      # heyy, heyyy -> hey
        text = re.sub(r"\b(h)(e+)(l+)(o+)\b", "hello", text) # hellooo -> hello
        return text

    @classmethod
    def _detect_language(cls, text: str) -> str:
        """Detect language (simplified heuristic for now)."""
        # In production, use langdetect or fasttext
        # Fallback to English for this iteration
        return "en"

    @classmethod
    def _detect_question_type(cls, text: str) -> str:
        """Detect the primary interrogative word."""
        for q_type, pattern in cls.QUESTION_TYPES.items():
            if re.search(pattern, text):
                return q_type
        return "statement"

    @classmethod
    def _detect_response_expectation(cls, text: str) -> str:
        """Detect if the user explicitly wants a table, list, timeline, etc."""
        if re.search(r"\btable\b|\bformat as table\b|\bcolumns\b", text):
            return "table"
        if re.search(r"\blist\b|\bbullet points\b", text):
            return "list"
        if re.search(r"\btimeline\b|\bchronological\b", text):
            return "timeline"
        if re.search(r"\bcompare\b|\bdifference\b|\bvs\b", text):
            return "comparison"
        if re.search(r"\bstep\b|\bhow to\b|\bprocess\b", text):
            return "workflow"
        return "standard"

    @classmethod
    def _extract_abbreviations(cls, text: str) -> list[str]:
        """Extract uppercase abbreviations (e.g. AWS, SSO) before lowercasing."""
        # Find 2+ uppercase letters
        matches = re.findall(r"\b[A-Z]{2,}\b", text)
        return list(set(matches))
