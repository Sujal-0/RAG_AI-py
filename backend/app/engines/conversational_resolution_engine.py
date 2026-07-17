"""Conversational Resolution Engine.

Responsible for deterministic query rewriting, pronoun resolution, and multi-intent 
splitting based on ConversationState before routing decisions are made.
"""

import re
import time
import logging
from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult
from app.utils.session import SessionStore

logger = logging.getLogger("app")

FOLLOW_UP_PHRASES = {
    "tell me more", "explain", "explain this", "continue", "next one",
    "what else", "anything more", "give examples", "summarize", "explain simply",
    "elaborate", "tell me in detail", "more details", "what about",
    "yes", "no", "okay"
}

COMPARISON_PHRASES = {
    "compare them", "which is better", "which comes first", "what happened next"
}

PRONOUNS = {"it", "them", "that", "this", "they", "he", "she"}

class ConversationalResolutionEngine(BaseEngine):
    """Rewrites queries using context and splits multi-intent requests."""

    def execute(self, context: ConversationContext) -> EngineResult:
        start_time = time.perf_counter()
        query = context.resolved_query or context.normalized_query or ""
        
        if not query.strip():
            return EngineResult(handled=False, reason_code="CONVERSATION_RESOLUTION_SKIPPED")

        state = SessionStore.get_state(context.session_id)
        
        # 1. Multi-Intent Splitting
        q_lower = query.lower()
        
        multi_intent_split = []
        if any(w in q_lower for w in [" and ", ", ", " also "]):
            parts = re.split(r'\s+and\s+|,\s+|\s+also\s+', q_lower)
            if len(parts) > 1:
                multi_intent_split = [p.strip() for p in parts if p.strip()]
                context.metadata["multi_intent"] = multi_intent_split
        
        # 2. Topic Switch Detection
        # Heuristic topic detection for current query
        current_topic = None
        if "policy" in q_lower: current_topic = "Policy"
        elif "project" in q_lower or "service" in q_lower: current_topic = "Company Info"
        elif "hr" in q_lower or "leave" in q_lower: current_topic = "HR Policies"
        elif "security" in q_lower: current_topic = "Security"
        
        if current_topic and state.active_topic and current_topic != state.active_topic:
            # Topic switch detected
            logger.info(f"Topic Switch Detected: {state.active_topic} -> {current_topic}")
            state.active_topic = current_topic
            state.active_heading = None
            state.active_entities = []
            state.active_document = None
            context.metadata["topic_switched"] = True
        elif current_topic:
            state.active_topic = current_topic
        
        # 3. Pronoun & Follow-up Resolution
        is_follow_up = False
        resolved_query = query
        confidence = 1.0 # 1.0 means no resolution needed, perfectly confident in original query
        
        clean_q = re.sub(r"[^\w\s]", "", q_lower).strip()
        if clean_q in FOLLOW_UP_PHRASES or clean_q in COMPARISON_PHRASES:
            is_follow_up = True
            
        if q_lower.startswith("what about ") and len(q_lower) > 11:
            topic = query[11:].strip(" ?.")
            resolved_query = f"Tell me about {state.active_company or 'Mobiloitte'} {topic}"
            is_follow_up = True
        elif q_lower.startswith("and ") and len(q_lower) > 4:
            topic = query[4:].strip(" ?.")
            resolved_query = f"Tell me about {state.active_company or 'Mobiloitte'} {topic}"
            is_follow_up = True
            
        short_qs = {"why", "how", "when", "where", "which one"}
        if clean_q in short_qs:
            is_follow_up = True

        if is_follow_up:
            if state.active_topic:
                if clean_q in FOLLOW_UP_PHRASES or clean_q in short_qs:
                    resolved_query = f"{query} regarding {state.active_topic} {state.active_heading or ''}".strip()
                    confidence = 0.9
                elif clean_q in COMPARISON_PHRASES:
                    resolved_query = f"Compare details regarding {state.active_topic} {state.active_heading or ''}".strip()
                    confidence = 0.9
            else:
                # Follow up but no active topic! Very low confidence.
                confidence = 0.3
                
        # Pronoun replacement
        words = resolved_query.split()
        replaced = False
        for i, w in enumerate(words):
            clean_w = w.lower().strip("?,.!")
            if clean_w in PRONOUNS:
                if state.active_entities:
                    words[i] = w.replace(clean_w, state.active_entities[-1], 1) if clean_w == w else state.active_entities[-1]
                    replaced = True
                    confidence = min(confidence, 0.8) # Decent confidence if we have entities
                elif state.active_company and clean_w in {"they", "them", "their", "it"}:
                    words[i] = w.replace(clean_w, state.active_company, 1) if clean_w == w else state.active_company
                    replaced = True
                    confidence = min(confidence, 0.9)
                elif state.active_topic:
                    words[i] = w.replace(clean_w, state.active_topic, 1) if clean_w == w else state.active_topic
                    replaced = True
                    confidence = min(confidence, 0.7)
                else:
                    # Pronoun found but no context!
                    confidence = min(confidence, 0.2)
                
        if replaced:
            resolved_query = " ".join(words)

        if resolved_query != query:
            logger.info(f"Conversational Rewrite (Conf: {confidence}): '{query}' -> '{resolved_query}'")
            context.resolved_query = resolved_query
            context.metadata["original_resolved_query"] = query
            context.metadata["was_rewritten"] = True
            
        context.metadata["resolution_confidence"] = confidence
        
        # If confidence is too low, we flag it for clarification
        if confidence < 0.5:
            context.metadata["requires_clarification"] = True

        return EngineResult(
            handled=False,
            reason_code="CONVERSATION_RESOLUTION_COMPLETED",
            metadata={"execution_ms": round((time.perf_counter() - start_time) * 1000, 2)}
        )

    @property
    def name(self) -> str:
        return "ConversationalResolution"
