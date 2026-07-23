"""Decision Engine for the Conversation Intelligence Platform.

Classifies queries instantaneously to skip Retrieval/Generation pipelines 
whenever possible (e.g. for greetings or small talk).
"""

import logging
import re
from typing import Any
from app.conversation.planner.query_normalizer import QueryNormalizer

from app.conversation.planner.gibberish_detector import EnterpriseGibberishDetector
from app.conversation.planner.query_normalizer import QueryNormalizer

class DecisionEngine:
    """Classifies user input into deterministic enterprise intents."""
    
    INTENT_PATTERNS = {
        "Greeting": [
            r"^(hi|hiya|hello|hey|greetings|yo|sup|wassup|namaste|namaskar|hola|bonjour|salaam|good morning|good afternoon|good evening|good night)\b"
        ],
        "Goodbye": [r"^(bye|goodbye|see you|see ya|farewell|cya|take care|gn|good night)\b"],
        "Thanks": [r"^(thanks|thank you|thankyou|thank u|thx|ty|tysm|appreciate it)\b"],
        "AssistantIdentity": [r"^(who are you|what is your name|your name|who made you|who built you|who created you|are you chatgpt|what are you|what can you do|your identity|tell me about yourself)\b"],
        "Help": [r"^(help|support|assist)\b"],
        "Clarification": [r"^(can you clarify|clarify|what do you mean)\b"],
        
        "ConversationFollowUp": [r"^(what about|tell me more|continue|explain further|and\b|what next|what else|also|how about)\b"],
        "Summary": [r"\b(summarize|summary|tl;dr|tldr|in short|briefly)\b"],
        "Comparison": [r"\b(compare|comparison|difference between|vs\.?|versus)\b"],
        "Table": [r"\b(table|format as table|tabular)\b"],
        "List": [r"\b(list|all of|enumerate)\b"],
        "Timeline": [r"\b(timeline|history|when did|dates|chronology)\b"],
        "Steps": [r"\b(steps|how to|how do i|how can i|procedure|guide|instructions)\b"],
        "Advantages": [r"\b(advantages|benefits|pros|good things|upside)\b"],
        "Disadvantages": [r"\b(disadvantages|drawbacks|cons|bad things|downside)\b"],
        "FAQ": [r"\b(faq|frequently asked questions)\b"],
        "Definition": [r"^(what is|define|meaning of)\b"],
        "Explanation": [r"^(explain|how does|why does|tell me about)\b"],
        "DocumentSearch": [r"\b(find in document|search document|where in the text)\b"],
        "SmallTalk": [r"^(how are you|what's up|whats up|how do you do)\b"]
    }

    @classmethod
    def classify(cls, query: str) -> dict[str, Any]:
        """
        Classifies the query and returns structured data.
        Returns: {"intent": str, "confidence": float, "reason": str, "processed_query": str}
        """
        norm = QueryNormalizer.normalize(query)
        
        # 1. Empty Check
        if not norm:
            return {"intent": "Empty", "confidence": 1.0, "reason": "Query is empty", "processed_query": ""}
            
        original_norm = norm
            
        # 2. Greeting variants
        greeting_matched = False
        
        for pattern in cls.INTENT_PATTERNS["Greeting"]:
            match = re.match(pattern, norm)
            if match:
                greeting_matched = True
                matched_text = match.group(0)
                norm = norm[len(matched_text):].strip()
                norm = re.sub(r'^(ai|bot|mobiloitte|there|bro|ji|buddy|assistant)\b', '', norm).strip()
                break
                
        if greeting_matched and not norm:
            return {"intent": "Greeting", "confidence": 1.0, "reason": "Exact greeting match", "processed_query": original_norm}
            
        # 3. Gibberish check 
        if EnterpriseGibberishDetector.is_gibberish(norm):
             return {
                 "intent": "Gibberish", 
                 "confidence": 0.99, 
                 "reason": "Detected keyboard spam or low quality query", 
                 "processed_query": norm,
                 "greeting_matched": greeting_matched
             }
             
        # 4. FastPath Priority Strict Ordering
        strict_order = ["Thanks", "Goodbye", "AssistantIdentity", "Help", "Clarification"]
        for intent in strict_order:
            for pattern in cls.INTENT_PATTERNS[intent]:
                if re.search(pattern, norm):
                    # For Identity, we don't care if there was a greeting, it's just Identity
                    if intent == "AssistantIdentity":
                        return {"intent": intent, "confidence": 1.0, "reason": "Matched identity", "processed_query": norm, "greeting_matched": greeting_matched}
                    return {"intent": intent, "confidence": 1.0, "reason": f"Matched {intent}", "processed_query": norm, "greeting_matched": greeting_matched}

        # If it reached here and greeting was matched but there is still text, it's a Knowledge/FollowUp query (Greeting + Question)
        
        # 5. Check FollowUp and other specific knowledge intents
        for pattern in cls.INTENT_PATTERNS["ConversationFollowUp"]:
            if re.search(pattern, norm):
                return {"intent": "ConversationFollowUp", "confidence": 0.98, "reason": "Matched follow-up pattern", "processed_query": norm, "greeting_matched": greeting_matched}
                
        for intent, patterns in cls.INTENT_PATTERNS.items():
            if intent in ["Greeting", "Goodbye", "Thanks", "AssistantIdentity", "Help", "Clarification", "ConversationFollowUp"]:
                continue
            for pattern in patterns:
                if re.search(pattern, norm):
                    return {"intent": intent, "confidence": 0.95, "reason": f"Matched {intent.lower()} keywords", "processed_query": norm, "greeting_matched": greeting_matched}

        # 6. Knowledge Query Validation (Task 8)
        # Reject completely meaningless short combinations that survived gibberish detection
        if len(norm.replace(" ", "")) < 4 and norm not in ["who", "why", "how", "what", "when"]:
             return {"intent": "Gibberish", "confidence": 0.99, "reason": "Insufficient length or meaning", "processed_query": norm, "greeting_matched": greeting_matched}
             
        # 7. Fallback
        if len(norm.split()) >= 2:
            return {"intent": "KnowledgeQuery", "confidence": 0.85, "reason": "Defaulted to Knowledge Query", "processed_query": norm, "greeting_matched": greeting_matched}
            
        # 8. Unknown
        return {"intent": "Unknown", "confidence": 0.35, "reason": "No exact match found", "processed_query": norm, "greeting_matched": greeting_matched}
