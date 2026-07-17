"""Query Understanding Engine.

Acts as the intelligence facade. It executes NLP extraction (Entities, Keywords, Intents)
exactly once per conversational turn. The output is a fully resolved query context 
that prevents downstream engines (like Retrieval) from duplicating NLP work.
"""

import logging
from app.engines.query.entity_extractor import EntityExtractor
from app.engines.query.intent_detector import IntentDetector
from app.engines.query.keyword_extractor import KeywordExtractor
from app.engines.query.query_analyzer import NormalizedQuery

logger = logging.getLogger("app")


class QueryUnderstandingEngine:
    """Consolidates NLP extraction at the very top of the pipeline."""
    
    @classmethod
    def analyze(cls, query: str) -> NormalizedQuery:
        """Parse all semantic features of the query deterministically."""
        
        logger.info("Executing Query Understanding", extra={"structured_log": True, "stage": "QueryUnderstanding"})
        
        # In a fully migrated state, these would be refactored into app/conversation/intelligence/
        # but for now we consume the existing production engines to avoid duplicating code.
        
        entities = EntityExtractor.extract(query)
        intent = IntentDetector.detect(query)
        keywords = KeywordExtractor.extract(query)
        
        is_question = "?" in query or query.lower().startswith(("what", "how", "why", "when", "where", "can", "is", "does"))
        
        return NormalizedQuery(
            normalized_text=query.strip().lower(),
            language="en",
            is_question=is_question,
            response_expectation="standard", # Could be mapped from Intent
            entities=entities,
            intent=intent,
            keywords=keywords
        )
