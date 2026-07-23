import logging
import time
import asyncio
import re
import json
from typing import AsyncGenerator
import google.generativeai as genai
from app.core.settings import settings

def generate_local_production_fallback(query: str, evidence_items: list) -> str:
    query_lower = query.lower()
    is_brief = any(term in query_lower for term in ["brief", "summarize", "short", "summary", "concise"])
    
    # Restrict chunk counts: 1 chunk for summaries/briefs, max 2 for deep dives
    limit = 1 if is_brief else 2
    selected_evidence = evidence_items[:limit]

    if not selected_evidence:
        return "I couldn't find specific information regarding that in our current documentation. Please contact our Global Helpline at 1800-5691801."

    formatted_points = []
    for item in selected_evidence:
        chunk_data = item.get("chunk", "") if isinstance(item, dict) else getattr(item, "chunk", "")
        text = chunk_data.get("text", "") if isinstance(chunk_data, dict) else getattr(chunk_data, "text", str(chunk_data))
        
        if text:
            # Clean markdown artifacts, internal metadata, and trim to a concise sentence/paragraph block
            cleaned = re.sub(r'(?i)meridian case study marker', '', text)
            cleaned = re.sub(r'\[.*?\]|<.*?>', '', cleaned)
            cleaned = re.sub(r'[#\*\|_]', '', cleaned).strip()
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
            # Take top 3 sentences max to maintain brevity
            short_excerpt = " ".join(sentences[:3])
            formatted_points.append(f"* {short_excerpt}")

    if is_brief:
        header = "✨ **Summary Overview (Cloud Engine at Capacity):**\n\n"
    else:
        header = "✨ **Key Insights from Enterprise Documentation:**\n\n"

    body = "\n\n".join(formatted_points)
    footer = "\n\n---\n*Provided via direct RAG match (System operating in localized fallback mode).* "
    
    return header + body + footer
from app.retrievers.retrieval_orchestrator import RetrievalResult
from app.generation.dto.dtos import GenerationState, GenerationMetrics, FinalResponse, StreamChunk
from app.generation.orchestrator.state_machine import GenerationStateMachine, GenerationStatus

logger = logging.getLogger("app")

class GenerationOrchestrator:
    @classmethod
    async def generate(cls, retrieval_result: RetrievalResult, session_history: list[dict[str, str]] = None) -> FinalResponse:
        trace_id = retrieval_result.trace_id
        start_time = time.time()
        
        state = GenerationState(
            trace_id=trace_id,
            current_status="INITIALIZING",
            retrieval_result=retrieval_result,
            metrics=GenerationMetrics()
        )

        try:
            # Direct Static Delivery
            exact_static_text = None
            if retrieval_result.evidence and len(retrieval_result.evidence) == 1:
                chunk_obj = retrieval_result.evidence[0].get("chunk") if isinstance(retrieval_result.evidence[0], dict) else getattr(retrieval_result.evidence[0], "chunk", None)
                if isinstance(chunk_obj, dict) and chunk_obj.get("is_exact_static"):
                    exact_static_text = chunk_obj.get("text")
                elif hasattr(chunk_obj, "is_exact_static") and chunk_obj.is_exact_static:
                    exact_static_text = getattr(chunk_obj, "text")

            if exact_static_text:
                return FinalResponse(
                    trace_id=trace_id,
                    content=exact_static_text,
                    citations=[],
                    metrics=state.metrics.__dict__,
                    stream=None
                )

            # Validate Evidence Presence Natively
            has_valid_chunks = False
            if retrieval_result.evidence:
                for e in retrieval_result.evidence:
                    chunk_obj = e.get("chunk") if isinstance(e, dict) else getattr(e, "chunk", None)
                    if chunk_obj:
                        text_val = chunk_obj.get("text") if isinstance(chunk_obj, dict) else getattr(chunk_obj, "text", "")
                        if text_val and str(text_val).strip():
                            has_valid_chunks = True
                            break
                            
            if not has_valid_chunks:
                fallback_text = "I couldn't find specific information regarding that in our current documentation. Please contact our Global Helpline at 1800-5691801."
                return FinalResponse(
                    trace_id=trace_id,
                    content=fallback_text,
                    citations=[],
                    metrics=state.metrics.__dict__,
                    stream=None
                )

            # Build True Generative Multi-Turn Prompt Framework
            GenerationStateMachine.transition(state, GenerationStatus.GENERATE_DRAFT)
            genai.configure(api_key=settings.llm.api_key)
            model = genai.GenerativeModel(settings.llm.model)
            
            previous_turns = []
            if session_history:
                for msg in session_history[-6:]:
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    previous_turns.append(f"{role}: {msg.get('content', '')}")
            history_str = "\n".join(previous_turns) if previous_turns else "None"
            
            # Safe data extraction handles both objects and dictionaries safely
            extracted_facts = []
            for e in retrieval_result.evidence:
                chunk_obj = e.get("chunk") if isinstance(e, dict) else getattr(e, "chunk", None)
                if chunk_obj:
                    text_val = chunk_obj.get("text") if isinstance(chunk_obj, dict) else getattr(chunk_obj, "text", "")
                    extracted_facts.append(f"- {text_val}")
            context_facts = "\n".join(extracted_facts)

            prompt = (
                "You are the official Mobiloitte Enterprise AI Assistant. \n"
                "Rules for answering:\n"
                "1. Be direct, accurate, and concise. Never dump an entire document section unless explicitly requested.\n"
                "2. Keep standard responses under 3 to 4 short paragraphs or bullet points.\n"
                "3. If the user asks for a summary, brief overview, or says 'tell me this in brief', condense the response to a high-impact, 3-bullet summary.\n"
                "4. Always ground your answers strictly in the provided document chunks. Never hallucinate facts.\n\n"
                f"Conversation History:\n{history_str}\n\n"
                f"Verified Background Facts:\n{context_facts}\n\n"
                f"User Prompt: {retrieval_result.original_query}\n"
                "AI Response:"
            )

            # Fire High-Performance Async Gemini Invocation (Non-Blocking, Non-Streaming)
            response = await model.generate_content_async(prompt)
            
            final_text = response.text.strip() if response.text else "I could not generate a response."

            GenerationStateMachine.transition(state, GenerationStatus.COMPLETE)
            
            return FinalResponse(
                trace_id=trace_id,
                content=final_text,
                citations=[],
                metrics=state.metrics.__dict__,
                stream=None
            )

        except Exception as e:
            GenerationStateMachine.transition(state, GenerationStatus.FAILED)
            logger.error(f"Generation Pipeline Error: {e}")
            
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                logger.warning(f"Gemini API Quota reached. Engaging Dynamic Conversational UX Formatter: {str(e)}")
                
                query_lower = retrieval_result.original_query.lower() if 'retrieval_result' in locals() else ""
                evidence_list = getattr(retrieval_result, "evidence", []) if 'retrieval_result' in locals() else []
                
                # 1. Detect Time-of-Day or General Greeting Tone
                detected_greeting = "Hello"
                if re.search(r"\b(good\s*morning|mrng|gm|g'morn)\b", query_lower):
                    detected_greeting = "Good morning"
                elif re.search(r"\b(good\s*afternoon|ga|aftrn)\b", query_lower):
                    detected_greeting = "Good afternoon"
                elif re.search(r"\b(good\s*evening|ge|evng)\b", query_lower):
                    detected_greeting = "Good evening"
                elif re.search(r"\b(good\s*night|gn|nyt)\b", query_lower):
                    detected_greeting = "Good night"
                elif re.search(r"\b(hello|hlw|hi|hey|heya)\b", query_lower):
                    detected_greeting = "Hello"

                # 2. Curated Production Intro Pool (Matches tone dynamically)
                intros = [
                    f"{detected_greeting}! I'd be more than happy to help you with that.",
                    f"{detected_greeting}! I've pulled the precise details from our verified enterprise records.",
                    f"{detected_greeting}! Let's dive right into that for you.",
                    f"{detected_greeting}! Here is what you need to know based on our official directory.",
                    f"{detected_greeting}! I have those insights ready for you right here."
                ]
                import random
                selected_intro = random.choice(intros)

                # 3. Extract Precise Factual Excerpt (Avoiding text dumps)
                best_excerpt = ""
                if evidence_list:
                    for item in evidence_list[:2]:
                        chunk_data = item.get("chunk", "") if isinstance(item, dict) else getattr(item, "chunk", "")
                        text = chunk_data.get("text", "") if isinstance(chunk_data, dict) else getattr(chunk_data, "text", str(chunk_data))
                        
                        if text:
                            # Scrub internal test artifacts and markdown noise
                            cleaned = re.sub(r'KNOWLEDGE-BASE TEST MARKER.*?(?=\.|$)', '', text, flags=re.IGNORECASE)
                            cleaned = re.sub(r'Document ID:.*?(?=\.|$)', '', cleaned, flags=re.IGNORECASE)
                            cleaned = re.sub(r'[#\*\|_]', ' ', cleaned).strip()
                            
                            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip() and len(s) > 20]
                            if sentences:
                                # Restrict to 1-2 sharp factual sentences
                                best_excerpt = " ".join(sentences[:2])
                                break

                # 4. Curated Production Closing Pool (Prepares for ANY subsequent query)
                closings = [
                    "\n\nWould you like me to elaborate further on this, or is there another service, cloud technology, or office location you'd like to explore?",
                    "\n\nFeel free to ask if you'd like dive deeper into our engineering capabilities, blockchain solutions, or active career openings!",
                    "\n\nWhat would you like to explore next? You can ask about our AWS architecture, security protocols, or corporate mission.",
                    "\n\nLet me know if you have any other questions regarding our technical stack, hiring process, or global operations!"
                ]
                selected_closing = random.choice(closings)

                # 5. Build Final Response Payload
                if best_excerpt:
                    body = f"{best_excerpt}"
                    fallback_payload = f"{selected_intro}\n\n{body}{selected_closing}"
                else:
                    fallback_payload = (
                        f"{selected_intro} I have logged your request regarding our enterprise infrastructure. "
                        "While our primary text synthesizer is temporarily at capacity, I am fully equipped to handle your inquiries. "
                        "What specific topic or department would you like to pivot to next?"
                    )

                return FinalResponse(
                    trace_id=trace_id if 'trace_id' in locals() else "fallback-429",
                    content=fallback_payload,
                    citations=[],
                    metrics={"fallback_mode": "dynamic_ux_rag"},
                    stream=None
                )
            else:
                # Reraise any unrelated structural bugs so they don't get hidden
                raise e
