"""Conversation Resolver Engine.

Tracks conversational memory across turns to maintain topic continuity, 
detect pronouns (he/it/they), and retain entity context for the Query Rewriter.
"""

import logging
import re
from typing import Optional

from app.core.settings import settings

logger = logging.getLogger("app")

class ConversationResolver:
    """Maintains and resolves conversational state by rewriting queries via LLM."""

    # Pronouns that indicate context dependency
    PRONOUNS = {"it", "they", "them", "he", "him", "she", "her", "this", "that", "these", "those"}

    @staticmethod
    def resolve_followup_locally(current_query: str, history: list) -> str:
        query_lower = current_query.lower()
        
        # Extract the last substantive user topic from history if available
        last_user_topic = ""
        if history:
            for msg in reversed(history):
                if msg.get("role") == "user" or msg.get("sender") == "user":
                    content = msg.get("content", "")
                    # Strip greetings or fluff to isolate the core subject
                    cleaned = re.sub(r'\b(hi|hello|gm|hey|tell|about|what|is|the)\b', '', content.lower())
                    if len(cleaned.strip()) > 3:
                        last_user_topic = content
                        break

        # Pronoun and continuity check
        pronouns = ["it", "they", "he", "she", "this", "that", "its", "their"]
        has_pronoun = any(re.search(r'\b' + p + r'\b', query_lower) for p in pronouns)
        
        is_short_followup = len(query_lower.split()) <= 5
        is_summary_request = any(term in query_lower for term in ["brief", "summarize", "short", "summary", "detail"])

        # Construct a context-injected search string
        if (has_pronoun or is_short_followup or is_summary_request) and last_user_topic:
            # Clean historical text symbols
            clean_history_topic = re.sub(r'[#\*>\n]', ' ', last_user_topic)
            resolved_query = f"{current_query} regarding {clean_history_topic}"
            return resolved_query
            
        return current_query

    @classmethod
    async def resolve_state(
        cls, 
        current_query: str, 
        session_history: list[dict[str, str]],
        current_entities: dict[str, list[str]]
    ) -> str:
        """Analyze current query against history and rewrite if it contains pronouns or lacks context."""
        
        if not session_history:
            return current_query

        # Extract recent context
        previous_turns = []
        # Get up to 6 messages to ensure we capture the last 3 full turns (user+assistant)
        for msg in session_history[-6:]:  
            role = "User" if msg.get("role") == "user" else "Assistant"
            previous_turns.append(f"{role}: {msg.get('content', '')}")
                
        if not previous_turns:
            return current_query
                
        # We aggressively execute the network call to the Gemini API if there is history.
        # Do not short-circuit locally.
            
        try:
            import google.generativeai as genai
            import asyncio
            
            if not settings.llm.api_key:
                logger.warning("LLM API Key missing. Falling back to original query.", extra={"structured_log": True, "stage": "ConversationResolver"})
                return current_query

            genai.configure(api_key=settings.llm.api_key)
            model = genai.GenerativeModel(settings.llm.model)
            
            history_str = "\n".join(previous_turns)
            prompt = (
                "You are an advanced Contextual Query Resolution Engine. Look at the entire conversation history. "
                "The user's latest turn may be a follow-up to a previous follow-up. Deduce the core target entity "
                "and all nested modifiers. Output a single, standalone search expression containing all hidden context. "
                "Output ONLY the resolved search string without quotes or conversational filler.\n\n"
                f"Conversation History:\n{history_str}\n\n"
                f"Latest Query: {current_query}\n"
                "Resolved Query:"
            )
            
            logger.info("Executing stateless LLM rewrite...", extra={"structured_log": True, "stage": "ConversationResolver"})
            print(f">>> [RESOLVER HISTORY SENT]: {previous_turns}")
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response.text:
                rewritten = response.text.strip().strip('"').strip("'")
                logger.info(
                    "Query Rewritten successfully",
                    extra={"structured_log": True, "stage": "ConversationResolver", "original": current_query, "rewritten": rewritten}
                )
                return rewritten
                
        except ImportError as e:
            logger.warning(
                f"google.generativeai not installed: {e}. Falling back to original query.",
                extra={"structured_log": True, "stage": "ConversationResolver"}
            )
            return current_query
        except Exception as e:
            print(f"!!! [CRITICAL RESOLVER CRASH]: {str(e)}")
            logger.error(
                f"[STRUCTURAL_EXCEPTION_TRACKER] LLM Rewrite failed: {e}. Falling back to original query.",
                extra={"structured_log": True, "stage": "ConversationResolver"}
            )
            
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str:
                query_lower = current_query.lower()
                loc_triggers = ["where", "located", "location", "office", "address", "hq"]
                
                if any(trigger in query_lower for trigger in loc_triggers):
                    # Reset target focus if looking for structural corporate assets, overriding previous entity
                    local_keyword_blend = f"{current_query} office operational footprint global presence"
                else:
                    # Invoke deterministic local resolver
                    local_keyword_blend = cls.resolve_followup_locally(current_query, session_history)
                    
                logger.warning("Gemini 429 Limit Breached. Activating Local Contextual Keyword Blend.")
                return local_keyword_blend
                
            # Context Fallback Matrix
            words = set(re.findall(r'\b\w+\b', current_query.lower()))
            pronouns = {"he", "his", "him", "she", "her", "they", "them", "it"}
            
            if words.intersection(pronouns) and session_history:
                last_user_query = ""
                for msg in reversed(session_history[-2:]):
                    if msg.get("role") == "user":
                        last_user_query = msg.get("content", "")
                        break
                if last_user_query:
                    return f"{current_query} {last_user_query}"
            
        return current_query
