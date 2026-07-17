"""LLM Generation Engine using Gemini.

Responsible for prompt construction, context formatting, LLM interaction,
and citation mapping. This layer is entirely isolated from retrieval logic.
"""

import logging
import re
import time
from typing import Any, AsyncGenerator

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.settings import settings
from app.engines.rag_engine import AnswerGenerator
from app.pipeline.context import ConversationContext
from app.utils.session import SessionStore

logger = logging.getLogger("app")

class CircuitBreaker:
    def __init__(self, failure_threshold=3, cooldown=60):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self.failures = 0
        self.last_failure_time = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        logger.warning(f"CircuitBreaker failure recorded. Total: {self.failures}")

    def record_success(self):
        if self.failures > 0:
            logger.info("CircuitBreaker reset on success.")
        self.failures = 0

    def is_open(self):
        if self.failures >= self.failure_threshold:
            if time.time() - self.last_failure_time > self.cooldown:
                self.failures = 0
                return False
            return True
        return False

gemini_circuit_breaker = CircuitBreaker()

def is_safe_query(query: str) -> bool:
    """Input Safety Layer to protect against prompt injection."""
    unsafe_patterns = [
        r"(?i)ignore previous instructions",
        r"(?i)reveal prompt",
        r"(?i)reveal your prompt",
        r"(?i)system prompt",
        r"(?i)bypass",
        r"(?i)embeddings",
        r"(?i)hidden instructions",
    ]
    for pattern in unsafe_patterns:
        if re.search(pattern, query):
            return False
    return True

from app.validators.response_validator import validate_llm_output



SYSTEM_PROMPT = """You are an Enterprise AI Knowledge Assistant for Mobiloitte.
Your ONLY purpose is to answer employee queries using the provided document context.

# MANDATORY RULES
1. Ground only on retrieved evidence. NEVER hallucinate or guess.
2. If the answer is not fully contained in the context, clearly state: "I couldn't find enough information in the uploaded documents."
3. No metadata leakage. NEVER output UUIDs, chunk IDs, or internal filenames in the body of your response.
4. Keep your tone professional, natural, conversational, and highly readable.
5. Be concise and get straight to the point.
6. Do NOT generate a "Sources" section at the bottom. The system will append the sources automatically.

# DYNAMIC ANSWER FORMATTING
Adapt your format strictly based on the query intent:
- Definitions/Concepts: Provide a short, direct 1-2 sentence paragraph.
- Comparisons/Differences: Use a Markdown Table for clear visual distinction.
- Lists/Multiple Items: Use concise Bullet Points.
- Procedures/How-tos: Use Numbered Steps in exact sequential order.
- Summaries: Use short, grouped paragraphs.
- Large Reports: Use clear Section Headings (`###`) to divide topics.

# RESPONSE EXECUTION
- Start with a direct, natural answer.
- Seamlessly integrate facts into your prose without robotic brackets.
"""


class GeminiAnswerGenerator(AnswerGenerator):
    """Generates cited responses using Gemini 2.5 Flash."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.llm.api_key)
        self.model = settings.llm.model

    def _build_context_and_citations(self, chunks: list[dict[str, Any]]) -> tuple[str, list[str]]:
        """Deduplicates chunks, formats context, and prepares citation map."""
        if not chunks:
            return "", []

        unique_citations = []
        for c in chunks:
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            citation_key = (filename, page)
            if citation_key not in unique_citations:
                unique_citations.append(citation_key)

        context_lines = []
        for c in chunks:
            filename = c.get("filename") or "Document"
            page = c.get("page_number", 1)
            citation_idx = unique_citations.index((filename, page)) + 1
            
            text = c.get("text", "").strip()
            heading = c.get("heading") or c.get("section") or "General"
            
            context_lines.append(f"--- Document: {filename} | Section: {heading} | Citation: [{citation_idx}] ---\n{text}")

        context_str = "\n\n".join(context_lines)

        citation_strings = []
        for i, (fn, pg) in enumerate(unique_citations):
            citation_strings.append(f"{fn} — Page {pg}")

        return context_str, citation_strings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
    def _generate_sync_with_retry(self, history: list, config: Any) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=history,
            config=config
        )
        return response.text or ""

    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False) -> str | AsyncGenerator[str, None]:
        """Synthesize query response using matching context chunks."""
        if not chunks:
            raise ValueError("No chunks provided to Gemini generator.")
            
        if gemini_circuit_breaker.is_open():
            raise RuntimeError("Gemini Circuit Breaker is OPEN.")
            
        if not is_safe_query(query):
            raise ValueError("Input safety violation detected.")

        context_str, citations = self._build_context_and_citations(chunks)

        # Build prompt
        prompt = f"<context>\n{context_str}\n</context>\n\nUser Query: {query}"
        
        prompt_size = len(prompt)
        chunk_count = len(chunks)
        provider = "Gemini"
        
        logger.info(
            "PROVIDER DIAGNOSTICS [START]\n"
            "Provider: %s\n"
            "Chunk count: %d\n"
            "Prompt size (chars): %d",
            provider, chunk_count, prompt_size
        )

        # Fetch conversation history
        history = []
        if session_id:
            raw_history = SessionStore.get_history(session_id, limit=5)
            for role, text in raw_history:
                # Convert our roles to Gemini roles ('user' or 'model')
                gemini_role = "user" if role == "user" else "model"
                history.append(types.Content(role=gemini_role, parts=[types.Part.from_text(text=text)]))

        # Add current prompt
        history.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        )

        sources_footer = "\n\n**Sources:**\n" + "\n".join(citations)

        if stream:
            async def generate_stream():
                try:
                    start_gen = time.perf_counter()
                    response_stream = await self.client.aio.models.generate_content_stream(
                        model=self.model,
                        contents=history,
                        config=config
                    )
                    full_answer = ""
                    first_token_time = None
                    async for chunk in response_stream:
                        if first_token_time is None:
                            first_token_time = (time.perf_counter() - start_gen) * 1000
                        if chunk.text:
                            full_answer += chunk.text
                            yield chunk.text
                    
                    total_latency = (time.perf_counter() - start_gen) * 1000
                    logger.info(
                        "PROVIDER DIAGNOSTICS [END]\n"
                        "Provider: %s\n"
                        "TTFT (ms): %.2f\n"
                        "Generation Latency (ms): %.2f\n"
                        "Finish Reason: SUCCESS",
                        provider, first_token_time or 0.0, total_latency
                    )
                    
                    if not validate_llm_output(full_answer):
                        raise ValueError("LLM Output Validation failed on streaming response.")
                        
                    gemini_circuit_breaker.record_success()
                    yield sources_footer
                except Exception as e:
                    gemini_circuit_breaker.record_failure()
                    import traceback
                    logger.error("Streaming generation failed: %s\n%s", e, traceback.format_exc())
                    raise

            return generate_stream()
        else:
            try:
                start_gen = time.perf_counter()
                answer = self._generate_sync_with_retry(history, config)
                total_latency = (time.perf_counter() - start_gen) * 1000
                logger.info(
                    "PROVIDER DIAGNOSTICS [END]\n"
                    "Provider: %s\n"
                    "TTFT (ms): %.2f\n"
                    "Generation Latency (ms): %.2f\n"
                    "Finish Reason: SUCCESS",
                    provider, total_latency, total_latency
                )
                
                if not validate_llm_output(answer):
                    raise ValueError("LLM Output Validation failed.")
                gemini_circuit_breaker.record_success()
                return answer + sources_footer
            except Exception as e:
                gemini_circuit_breaker.record_failure()
                import traceback
                logger.error("Generation failed: %s\n%s", e, traceback.format_exc())
                raise
