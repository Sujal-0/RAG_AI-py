"""Knowledge retrieval engine.

Resolves responses, suggested follow-up questions, and metadata
for confident topic matches from the centralized knowledge base.
"""

import time

from app.configs.knowledge import KNOWLEDGE_DATABASE
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult


class KnowledgeEngine(BaseEngine):
    """Retrieves answers and suggestions from the configuration-driven knowledge base."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()

        decision = context.metadata.get("decision")
        if decision != "FASTPATH":
            return EngineResult(
                handled=False,
                reason_code="KNOWLEDGE_NO_INTENT",
            )

        intent_id = context.intent

        if not intent_id:
            return EngineResult(
                handled=False,
                reason_code="KNOWLEDGE_NO_INTENT",
            )

        # Search for entries matching all detected intents
        matched_intents = context.metadata.get("matched_intents", [intent_id])

        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

        entries = []
        for i_id in matched_intents:
            e = next((e for e in KNOWLEDGE_DATABASE if e.intent_id == i_id), None)
            if e:
                entries.append(e)

        if entries:
            if len(entries) > 1:
                # Group and combine answers naturally
                context.response = "\n\n".join(f"[{e.title}]\n{e.answer}" for e in entries)
            else:
                context.response = entries[0].answer

            # Save suggestions in metadata
            context.metadata["suggested_questions"] = entries[0].suggested_questions
            context.metadata["title"] = entries[0].title

            metadata = {
                "title": entries[0].title,
                "answer": context.response,
                "suggested_questions": entries[0].suggested_questions,
                "execution_ms": duration_ms,
                "matched_intents": matched_intents,
            }

            return EngineResult(
                handled=True,
                reason_code=f"KNOWLEDGE_RETRIEVED_{intent_id}",
                metadata=metadata,
            )

        return EngineResult(
            handled=False,
            reason_code="KNOWLEDGE_NO_KB_MATCH",
        )

    @property
    def name(self) -> str:
        return "KnowledgeRetrieval"
