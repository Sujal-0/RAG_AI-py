"""Conversation Orchestrator.

The absolute controller of the entire AI system. It orchestrates the Planner, 
Graph, Memory, Retrieval, and Generation platforms.
"""

import logging
import time
import uuid

from app.core.settings import settings
from app.conversation.dto.dtos import ConversationSession, FinalConversationResponse
from app.conversation.planner.planner import ConversationPlanner
from app.conversation.memory.memory_manager import MemoryManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.retrievers.retrieval_orchestrator import RetrievalOrchestrator
from app.generation.orchestrator.generation_orchestrator import GenerationOrchestrator

logger = logging.getLogger("app")


class ConversationOrchestrator:
    """The master controller for processing user queries."""
    
    @classmethod
    async def process_turn(cls, db_session: AsyncSession, query: str, session_id: str) -> FinalConversationResponse:
        """Executes a single conversational turn."""
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(
            "Conversation Started", 
            extra={"structured_log": True, "trace_id": trace_id, "session_id": session_id, "stage": "ConversationOrchestrator"}
        )
        
        # 1. Load/Initialize Session from Memory Manager
        session = MemoryManager.get_session(session_id)
        session.trace_id = trace_id
        
        try:
            # 2. Plan Execution
            plan = ConversationPlanner.plan(query, session)
            
            # 3. Handle Fast-Paths (Clarifications, Empty, etc.)
            if (plan.fastpath or not plan.needs_retrieval) and plan.intent not in ["Greeting", "Gibberish"]:
                return FinalConversationResponse(
                    trace_id=trace_id,
                    content=plan.clarification_message,
                    intent=plan.intent,
                    is_clarification=True,
                    metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}}
                )
                
            # 4. Retrieval Execution
            print(f">>> [ConversationOrchestrator] Starting Retrieval Orchestrator for intent: {plan.intent}...")
            
            # Use processed query if available, fallback to original query
            effective_query = getattr(plan, "processed_query", query)
            
            # Smart Static Intercept (Pre-Resolver)
            import re
            import json
            from app.retrievers import static_knowledge

            history = session.short_memory
            query_raw = effective_query.strip()
            query_lower = query_raw.lower()

            # -------------------------------------------------------------
            # 1. TYPO CORRECTION & SYNONYM MAPPING
            # -------------------------------------------------------------
            typo_map = {
                "misison": "mission", "mision": "mission",
                "secuity": "security", "secutity": "security",
                "blockhain": "blockchain", "blockachin": "blockchain",
                "technolgy": "services", "technologies": "services",
                "tech stack": "services", "technical capabilities": "services",
                "engineering capabilities": "services", "tech stack": "services"
            }
            for typo, correct in typo_map.items():
                if typo in query_lower:
                    query_lower = query_lower.replace(typo, correct)

            # -------------------------------------------------------------
            # 1. STRICT TURN-LOCAL GREETING DETECTION (Production Grade)
            # -------------------------------------------------------------
            greeting_map = {
                r"\b(good\s*morning|mrng|gm|g'morn|gd\s*mrng|gud\s*mrng)\b": "Good morning!",
                r"\b(good\s*afternoon|ga|aftrn|gd\s*afternoon|gud\s*afternoon)\b": "Good afternoon!",
                r"\b(good\s*evening|ge|evng|gd\s*evening|gud\s*evening)\b": "Good evening!",
                r"\b(good\s*night|gn|gd\s*night|gud\s*night|nyt|nite)\b": "Good night!",
                r"\b(hello|hlo|hlw|hallo|helo)\b": "Hello!",
                r"\b(hi+|hii+|hey|heya|hiya|yo)\b": "Hi!"
            }
            
            explicit_greeting = ""
            for pat, canonical in greeting_map.items():
                if re.search(pat, query_lower):
                    explicit_greeting = canonical + " "
                    break

            # Short-circuit if the user ONLY typed a greeting
            clean_eval = query_lower
            for pat in greeting_map.keys():
                clean_eval = re.sub(pat, "", clean_eval)
            clean_eval = re.sub(r'[#\*_]', '', clean_eval).strip()
            
            if explicit_greeting and len(clean_eval) <= 3:
                reply = f"{explicit_greeting.strip()} How can I help you today?"
                return FinalConversationResponse(trace_id=trace_id, content=reply, intent=plan.intent, citations=[], metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}}, is_clarification=True, stream=None)

            # Clean query text for intent parsing
            clean_q = re.sub(r'[#\*_]', '', query_lower).strip()

            # -------------------------------------------------------------
            # 2. BULLETPROOF CONTINUATION & AFFIRMATION HANDLER ("yes", "tell me more")
            # -------------------------------------------------------------
            affirmative_patterns = r"^(yes|yep|sure|yeah|yea|y|ok|okay|please do|definitely|absolutely|tell me more|tell me more about it|more info)$"
            
            if re.match(affirmative_patterns, clean_q):
                target_topic = "services"
                if history:
                    for msg in reversed(history):
                        if isinstance(msg, dict):
                            content = str(msg.get("content") or msg.get("text") or "").lower()
                        else:
                            content = str(getattr(msg, "content", getattr(msg, "text", ""))).lower()
                            
                        if any(k in content for k in ["global presence", "office", "location", "delhi"]):
                            target_topic = "locations"
                            break
                        elif any(k in content for k in ["philosophy", "mantra", "experience", "mission"]):
                            target_topic = "mission"
                            break
                        elif any(k in content for k in ["blockchain", "web3", "cloud", "security", "tech stack"]):
                            target_topic = "services"
                            break
                        elif any(k in content for k in ["iffco", "case study", "portfolio"]):
                            target_topic = "case_studies"
                            break

                raw_expansion = static_knowledge.company_basics.get(target_topic, "Mobiloitte delivers comprehensive digital engineering solutions worldwide.")
                reply = f"Certainly! To expand further: {raw_expansion}\n\nWhat other area would you like to examine next?"
                return FinalConversationResponse(trace_id=trace_id, content=reply, intent=plan.intent, citations=[], metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}}, is_clarification=True, stream=None)

            # -------------------------------------------------------------
            # 3. NEGATION HANDLER ("no thanks", "all good")
            # -------------------------------------------------------------
            if re.match(r"^(no|nope|nah|n|no thanks|all good|im good|thanks|thank you)$", clean_q):
                reply = "Alright! Let me know if you need anything else. Have a great day!"
                return FinalConversationResponse(trace_id=trace_id, content=reply, intent=plan.intent, citations=[], metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}}, is_clarification=True, stream=None)

            # -------------------------------------------------------------
            # 4. COMPREHENSIVE MULTI-INTENT MATRIX
            # -------------------------------------------------------------
            intent_aliases = {
                "mission": [r"\bmission\b", r"\bgoal\b"],
                "vision": [r"\bvision\b"],
                "history": [r"\bhistory\b", r"\bfounded\b", r"\bstarted\b"],
                "security": [r"\bsecurity\b", r"\bcompliance\b", r"\bvapt\b"],
                "cloud": [r"\bcloud\b", r"\baws\b", r"\bdevops\b"],
                "blockchain": [r"\bblockchain\b", r"\bweb3\b"],
                "locations": [r"\bglobal presence\b", r"\boffice\b", r"\blocation\b", r"\bwhere\b", r"\bdelhi\b"],
                "careers": [r"\bcareer\b", r"\bhiring\b", r"\bjobs\b"],
                "case_studies": [r"\bcase stud\b", r"\bportfolio\b", r"\biffco\b"],
                "services": [r"\bservices\b", r"\btech stack\b", r"\bcapabilities\b", r"\bengineering\b"]
            }

            matched_intents = []
            for intent_key, aliases in intent_aliases.items():
                for alias in aliases:
                    if re.search(alias, clean_q):
                        if intent_key not in matched_intents:
                            matched_intents.append(intent_key)
                        break

            # Prevent redundant generic services wrapper if specific domains matched
            if "services" in matched_intents and len(matched_intents) > 1:
                matched_intents.remove("services")

            if matched_intents:
                import random
                intros = [
                    "I'd be delighted to share that with you.",
                    "Here are the key details from our official enterprise directory:",
                    "I've gathered that information for you right here:",
                    "Certainly! Let's walk through that."
                ]
                base_intro = random.choice(intros)
                prefix = f"{explicit_greeting}{base_intro}\n\n" if explicit_greeting else f"{base_intro}\n\n"
                
                formatted_blocks = []
                for intent in matched_intents:
                    raw_text = static_knowledge.company_basics.get(intent, "")
                    if raw_text and "currently being updated" not in raw_text:
                        title = intent.replace("_", " ").title()
                        formatted_blocks.append(f"### 💡 Mobiloitte {title}\n> {raw_text}\n")

                closings = [
                    "\nWould you like to explore our engineering services, cloud infrastructure, or global office locations next?",
                    "\nFeel free to ask if you'd like to dive deeper into our blockchain solutions, security protocols, or corporate mission!",
                    "\nWhat would you like to investigate next? You can ask about our career openings, AWS capabilities, or technical stack.",
                    "\nLet me know if you have any other questions regarding our enterprise services, security compliance, or hiring process!"
                ]

                if formatted_blocks:
                    final_content = prefix + "\n".join(formatted_blocks) + random.choice(closings)
                    return FinalConversationResponse(
                        trace_id=trace_id, 
                        content=final_content, 
                        intent=plan.intent, 
                        citations=[], 
                        metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}, "router": "production_fastpath_polished"}, 
                        is_clarification=True, 
                        stream=None
                    )
            # -------------------------------------------------------------
            # 5. STRICT GIBBERISH & NOISE FILTER
            # -------------------------------------------------------------
            from app.utils.conversation import is_probable_gibberish
            
            def strict_gibberish_check(text: str) -> bool:
                if is_probable_gibberish(text):
                    return True
                condensed = text.replace(" ", "").lower()
                # 4+ consecutive identical chars (e.g. hhhh, aaaa)
                if re.search(r'(.)\1{3,}', condensed):
                    return True
                # Known keyboard smashes
                if re.match(r'^(asdf|qwer|zxcv|hjkl)[a-z]*', condensed):
                    return True
                # Long string (8+ chars) with absolutely no vowels
                if len(condensed) >= 8 and not any(v in condensed for v in "aeiouy"):
                    return True
                # Pure symbols/numbers of length 5+ (e.g. 123123123)
                if len(condensed) >= 5 and not any(c.isalpha() for c in condensed):
                    return True
                return False

            if strict_gibberish_check(query_raw):
                reply = "I'm sorry, I didn't quite catch that. Could you please rephrase or let me know if you need help with our technical capabilities, cloud solutions, or enterprise architecture?"
                return FinalConversationResponse(trace_id=trace_id, content=reply, intent=plan.intent, citations=[], metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}}, is_clarification=True, stream=None)

            retrieval_result = await RetrievalOrchestrator.execute(
                session=db_session,
                raw_query=effective_query,
                session_history=session.short_memory[-6:],  # Last 3 turns for context
                plan=plan
            )
            
            # Ensure the planner's single source of truth intent overrides anything else
            retrieval_result.intent = plan.intent
            
            print(f">>> [ConversationOrchestrator] Retrieval Finished. Found {len(retrieval_result.evidence)} evidence items.")
            
            # 5. Generation Execution
            print(">>> [ConversationOrchestrator] Starting Generation Orchestrator...")
            gen_response = await GenerationOrchestrator.generate(
                retrieval_result, 
                session_history=session.short_memory[-6:]
            )
            print(">>> [ConversationOrchestrator] Generation Finished.")
            
            final_response = FinalConversationResponse(
                trace_id=gen_response.trace_id,
                content=gen_response.content,
                intent=plan.intent,
                citations=gen_response.citations,
                metrics=gen_response.metrics,
                debug_info={
                    "retrieval": retrieval_result.debug_info if retrieval_result and hasattr(retrieval_result, "debug_info") else {},
                    "generation_plan": getattr(gen_response, "plan", None)
                },
                is_clarification=False,
                stream=gen_response.stream
            )
            
            # 6. Append to Memory
            MemoryManager.append_turn(session_id, query, gen_response.content)
            
            final_response.metrics["duration_ms"] = final_response.metrics.get("durations_ms", {})
            final_response.metrics["duration_ms"]["total_ms"] = int((time.time() - start_time) * 1000)
            return final_response

        except ValueError as e:
            if "InsufficientEvidenceError" in str(e):
                return FinalConversationResponse(
                    trace_id=trace_id,
                    content="I couldn't find enough verified information.",
                    intent=plan.intent if 'plan' in locals() else "Unknown",
                    is_clarification=True,
                    metrics={"duration_ms": {"total_ms": int((time.time() - start_time) * 1000)}}
                )
            logger.error(f"Conversation pipeline error: {e}", exc_info=True, extra={"trace_id": trace_id})
            return FinalConversationResponse(
                trace_id=trace_id,
                content="I encountered an internal error while processing your request.",
                is_clarification=True
            )
        except Exception as e:
            logger.error(f"Conversation pipeline error: {e}", exc_info=True, extra={"trace_id": trace_id})
            return FinalConversationResponse(
                trace_id=trace_id,
                content="I encountered an internal error while processing your request.",
                is_clarification=True
            )
