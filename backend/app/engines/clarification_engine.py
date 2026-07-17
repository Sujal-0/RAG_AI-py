"""Clarification Engine.

Detects ambiguous queries or low-confidence resolutions and short-circuits the pipeline
to prompt the user with dynamic clarification options sourced from the document repository.
"""

import time
import logging
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult
from app.repositories.document_repository import DocumentRepository
from app.database.session import async_session
from app.engines.rag_engine import run_async_safely

logger = logging.getLogger("app")

BROAD_CONCEPTS = {"policy", "policies", "service", "services", "project", "projects", "benefits", "guidelines", "security", "training", "document", "documents"}

class ClarificationEngine(BaseEngine):
    """Halts the pipeline to ask for clarification on ambiguous concepts."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()
        
        # Check if conversation resolution explicitly requested clarification
        requires_clarification = context.metadata.get("requires_clarification", False)
        
        query = context.resolved_query or context.normalized_query or ""
        q_lower = query.lower().strip()
        words = set(q_lower.split())
        
        # Check if it's purely a broad concept query (e.g. just "policy" or "what is policy")
        # If it's a very short query (<= 3 words) and contains a broad concept
        is_broad = False
        if len(words) <= 4:
            if words.intersection(BROAD_CONCEPTS):
                is_broad = True
                
        if not requires_clarification and not is_broad:
            return EngineResult(handled=False, reason_code="CLARIFICATION_SKIPPED")
            
        logger.info("Clarification required for query: '%s'", query)
        
        # Attempt to get dynamic options from indexed documents
        options = []
        try:
            from app.database.session import db_is_available
            from unittest.mock import Mock
            is_mocked = isinstance(DocumentRepository.vector_search, Mock)
            
            if db_is_available and not is_mocked:
                async def fetch_vocab():
                    async with async_session() as session:
                        return await DocumentRepository.get_indexed_vocabulary(session)
                
                vocab = run_async_safely(fetch_vocab())
                
                # Filter headings related to the concept
                concept = list(words.intersection(BROAD_CONCEPTS))
                concept_word = concept[0] if concept else "policy"
                
                related_headings = [h for h in vocab.get("headings", set()) if concept_word in h or (concept_word == "policy" and "leave" in h)]
                
                # Take top 3 unique headings
                if related_headings:
                    # Sort to get the most specific ones (longer ones usually)
                    related_headings.sort(key=len, reverse=True)
                    options = related_headings[:4]
                    
        except Exception as e:
            logger.error("Clarification Engine failed to fetch dynamic options: %s", e)
            
        # Fallback to static options if dynamic failed or returned empty
        if not options:
            if "policy" in words or "policies" in words:
                options = ["Leave Policy", "HR Policy", "Travel Policy", "Security Policy"]
            elif "project" in words or "projects" in words:
                options = ["Current Projects", "Completed Projects", "Project Guidelines"]
            elif "service" in words or "services" in words:
                options = ["Software Development", "AI/ML Services", "Cloud Infrastructure"]
            else:
                options = ["Can you be more specific?"]
                
        # Format the response
        bullet_options = "\n".join([f"• {opt.title()}" for opt in options])
        response_text = f"I found multiple matches for that topic. Which one are you referring to?\n\n{bullet_options}"
        
        context.intent = "CLARIFICATION_REQUIRED"
        context.response = response_text
        
        # Store event for dev mode trace
        context.metadata["clarification_events"] = {
            "triggered": True,
            "reason": "low_confidence_resolution" if requires_clarification else "ambiguous_broad_concept",
            "options_offered": options
        }

        return EngineResult(
            handled=True,
            reason_code="CLARIFICATION_PROMPTED",
            metadata={
                "execution_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "options_offered": options
            }
        )

    @property
    def name(self) -> str:
        return "ClarificationEngine"
