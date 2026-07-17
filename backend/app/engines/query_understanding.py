"""Query understanding engine.

Analyzes the resolved query to determine the best matching knowledge topic
using a deterministic, layered confidence model.
"""

import re
import time

from app.configs.knowledge import KNOWLEDGE_DATABASE
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult

# Stop words ignored during keyword overlap checks to prevent false-positive collisions
STOP_WORDS = {
    "tell",
    "me",
    "about",
    "who",
    "what",
    "is",
    "are",
    "the",
    "of",
    "to",
    "your",
    "our",
    "how",
    "you",
    "do",
    "does",
    "any",
    "where",
    "can",
    "i",
    "we",
    "for",
    "in",
    "on",
    "at",
    "an",
    "a",
    "with",
    "there",
}


class QueryUnderstandingEngine(BaseEngine):
    """Classifies queries into knowledge topics using confidence scoring."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()
        query = context.resolved_query or ""
        tokens = context.tokens or []

        best_entry = None
        best_confidence = 0.0
        best_matched_keywords = []

        query_norm = context.normalized_query or ""
        query_res = context.resolved_query or ""
        # Create stop-word stripped token set
        query_token_set = set(t.lower() for t in tokens) - STOP_WORDS

        # Helper clean function for boundary-safe exact matches
        def clean_term(s: str) -> str:
            s_clean = s.lower().replace("_", " ")
            s_clean = re.sub(r"[’'‘]", "", s_clean)
            s_clean = re.sub(r"[?,.!;:()\-+=\[\]{}@#$%^&*~_/\\|<>]", " ", s_clean)
            s_clean = re.sub(r"\s+", " ", s_clean)
            return s_clean.strip()

        query_clean_norm = clean_term(query_norm)
        query_clean_res = clean_term(query_res)

        # Evaluate each knowledge entry in the database
        for entry in KNOWLEDGE_DATABASE:
            confidence = 0.0
            matched_kws = []

            title_clean = clean_term(entry.title)
            intent_clean = clean_term(entry.intent_id)

            # 1. Exact Match Check (1.00)
            is_exact = query_clean_res in (
                title_clean,
                intent_clean,
            ) or query_clean_norm in (title_clean, intent_clean)
            if not is_exact:
                for phrase in entry.trigger_phrases:
                    p_clean = clean_term(phrase)
                    if query_clean_norm == p_clean or query_clean_res == p_clean:
                        is_exact = True
                        break

            if is_exact:
                confidence = 1.00
            else:
                # 2. Phrase Match Check (0.99)
                has_phrase = False
                for phrase in entry.trigger_phrases:
                    p_clean = clean_term(phrase)
                    if len(p_clean.split()) > 1:
                        pattern = rf"\b{re.escape(p_clean)}\b"
                        if re.search(pattern, query_clean_norm) or re.search(
                            pattern, query_clean_res
                        ):
                            has_phrase = True
                            break

                if has_phrase:
                    confidence = 0.99
                else:
                    # 3. Keyword Overlap Check (0.95 / 0.82 / 0.63)
                    entry_kw_set = set(k.lower() for k in entry.keywords)
                    overlap = query_token_set.intersection(entry_kw_set)
                    matched_kws = list(overlap)

                    if len(overlap) >= 2:
                        confidence = 0.95
                    elif len(overlap) == 1:
                        confidence = 0.82
                    else:
                        # 4. Partial Keyword Match Check (0.63)
                        has_partial = False
                        for q_tok in query_token_set:
                            # Skip short partials to avoid noise
                            if len(q_tok) < 3:
                                continue
                            for kw in entry_kw_set:
                                if q_tok in kw or kw in q_tok:
                                    has_partial = True
                                    matched_kws.append(kw)
                                    break
                            if has_partial:
                                break
                        if has_partial:
                            confidence = 0.63

            # Update best match
            if confidence > best_confidence:
                best_confidence = confidence
                best_entry = entry
                best_matched_keywords = matched_kws

        duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

        # Select highest-confidence match exceeding its defined threshold
        if best_entry and best_confidence >= best_entry.threshold:
            context.intent = best_entry.intent_id

            # Check for multiple intents in the query
            matched_intents = [best_entry.intent_id]
            if any(conj in query.lower() for conj in ["and", "or", "with", ",", "&"]):
                for entry in KNOWLEDGE_DATABASE:
                    if entry.intent_id == best_entry.intent_id:
                        continue
                    entry_title = clean_term(entry.title)
                    if entry_title in query_clean_norm or entry_title in query_clean_res or any(clean_term(p) in query_clean_norm for p in entry.trigger_phrases):
                        matched_intents.append(entry.intent_id)
            context.metadata["matched_intents"] = list(dict.fromkeys(matched_intents))

            metadata = {
                "detected_topic": best_entry.title,
                "intent": best_entry.intent_id,
                "confidence": best_confidence,
                "matched_keywords": best_matched_keywords,
                "matched_intents": context.metadata["matched_intents"],
                "execution_ms": duration_ms,
            }

            # Stash properties in context metadata for response building and tracing
            context.metadata["detected_topic"] = best_entry.title
            context.metadata["confidence"] = best_confidence
            context.metadata["matched_keywords"] = best_matched_keywords

            return EngineResult(
                handled=False,
                reason_code=f"QUERY_UNDERSTANDING_MATCHED_{best_entry.intent_id}",
                metadata=metadata,
            )

        # No match found or confidence was below threshold
        metadata = {
            "detected_topic": None,
            "confidence": best_confidence,
            "matched_keywords": [],
            "execution_ms": duration_ms,
        }

        # Clear intent if confidence check failed
        context.intent = None
        context.metadata["confidence"] = best_confidence

        return EngineResult(
            handled=False,
            reason_code="QUERY_UNDERSTANDING_NO_CONFIDENT_MATCH",
            metadata=metadata,
        )

    @property
    def name(self) -> str:
        return "QueryUnderstanding"
