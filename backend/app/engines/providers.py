"""Multi-LLM Provider Orchestration Engine.

Manages LLM providers (Gemini, Ollama, OpenAI, Claude, Extractive) with health tracking,
dynamic priority, automatic failover, and quota management.
"""

import json
import logging
import time
import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional
from app.core.settings import settings
from app.engines.rag_engine import AnswerGenerator
from app.engines.llm_generator import GeminiAnswerGenerator

logger = logging.getLogger("app")

class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, name: str, priority: int):
        self.name = name
        self.priority = priority
        self.health_score = 100.0
        self.success_count = 0
        self.failure_count = 0
        self.total_latency = 0.0
        self.total_estimated_tokens = 0
        self.is_active = True
        self.consecutive_failures = 0
        self.context_window = 4096

    def record_success(self, latency_ms: float, estimated_tokens: int = 0) -> None:
        self.success_count += 1
        self.total_latency += latency_ms
        self.total_estimated_tokens += estimated_tokens
        self.health_score = min(100.0, self.health_score + 2.0)
        self.consecutive_failures = 0

    def record_failure(self, error: Exception) -> None:
        self.failure_count += 1
        self.consecutive_failures += 1
        self.health_score = max(0.0, self.health_score - 15.0)
        logger.warning(f"Provider {self.name} failed: {error}. New health: {self.health_score:.1f}")
        
        if self.consecutive_failures >= 5 or self.health_score < 30.0:
            self.is_active = False
            logger.error(f"Provider {self.name} disabled due to consecutive failures or critically low health.")

    @property
    def average_latency(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency / self.success_count

    def get_metrics(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "priority": self.priority,
            "health_score": round(self.health_score, 1),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_latency_ms": round(self.average_latency, 1),
            "total_estimated_tokens": self.total_estimated_tokens,
            "is_active": self.is_active
        }

    def _apply_token_budget(self, query: str, chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Token Budget Manager: Dynamically truncates chunks to fit provider window."""
        reserved_output = 512
        query_tokens = len(query) // 4
        remaining_budget = self.context_window - reserved_output - query_tokens
        
        selected = []
        used_tokens = 0
        
        for c in chunks:
            chunk_tokens = len(c.get("text", "")) // 4
            if remaining_budget - chunk_tokens > 0:
                selected.append(c)
                remaining_budget -= chunk_tokens
                used_tokens += chunk_tokens
            else:
                chars_left = remaining_budget * 4
                if chars_left > 100:
                    c_copy = c.copy()
                    c_copy["text"] = c.get("text", "")[:chars_left] + "... [TRUNCATED]"
                    selected.append(c_copy)
                    used_tokens += remaining_budget
                break
                
        budget_stats = {
            "context_window": self.context_window,
            "reserved_output": reserved_output,
            "query_tokens": query_tokens,
            "chunk_tokens": used_tokens,
            "remaining_budget": self.context_window - reserved_output - query_tokens - used_tokens
        }
        
        # Inject budget info into the first chunk's metadata temporarily so caller can log it if needed
        if selected:
            selected[0]["_budget_stats"] = budget_stats
            
        return selected, budget_stats

    @abstractmethod
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        pass


class OllamaProvider(LLMProvider):
    """Local Ollama instance integration."""
    def __init__(self):
        super().__init__(name="Ollama", priority=1)
        import os
        self.enabled = str(os.getenv("OLLAMA_ENABLED", "true")).lower() == "true"
        if not self.enabled:
            self.is_active = False
            
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.timeout = float(os.getenv("OLLAMA_TOTAL_TIMEOUT", "12.0"))
        self.ttft_timeout = float(os.getenv("OLLAMA_FIRST_TOKEN_TIMEOUT", "5.0"))
        self.context_window = 8192

    def _build_prompt(self, query: str, chunks: list[dict[str, Any]], response_plan: Any = None) -> str:
        context_str = "\n\n".join([f"Document: {c.get('filename')}\nContent: {c.get('text')}" for c in chunks])
        format_instr = getattr(response_plan, "structure_guidelines", "Respond clearly.") if response_plan else "Respond clearly."
        return f"System: Use the context below to answer. {format_instr}\n\nContext:\n{context_str}\n\nUser: {query}"
        
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        if not self.enabled:
            raise Exception("Ollama is disabled via environment variables.")
            
        chunks, budget = self._apply_token_budget(query, chunks)
        start = time.perf_counter()
        prompt = self._build_prompt(query, chunks, response_plan)
        est_tokens = len(prompt) // 4
        
        if stream:
            async def stream_wrapper():
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        async with client.stream("POST", f"{self.host}/api/generate", json={"model": self.model, "prompt": prompt, "stream": True}) as response:
                            response.raise_for_status()
                            iterator = response.aiter_lines()
                            
                            try:
                                first_line = await asyncio.wait_for(anext(iterator), timeout=self.ttft_timeout)
                                if first_line:
                                    data = json.loads(first_line)
                                    yield data.get("response", "")
                                    self.record_success((time.perf_counter() - start) * 1000, est_tokens)
                            except asyncio.TimeoutError:
                                raise TimeoutError(f"Ollama Time-To-First-Token exceeded ({self.ttft_timeout}s)")
                                
                            async for line in iterator:
                                if line:
                                    data = json.loads(line)
                                    yield data.get("response", "")
                except Exception as e:
                    self.record_failure(e)
                    raise
            return stream_wrapper()
        else:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.host}/api/generate", json={"model": self.model, "prompt": prompt, "stream": False})
                    response.raise_for_status()
                    answer = response.json().get("response", "")
                    latency = (time.perf_counter() - start) * 1000
                    self.record_success(latency, est_tokens + (len(answer)//4))
                    return answer
            except Exception as e:
                self.record_failure(e)
                raise


class GeminiProviderAdapter(LLMProvider):
    """Adapter for the existing Gemini generator."""
    def __init__(self):
        super().__init__(name="Gemini", priority=2)
        self.generator = GeminiAnswerGenerator()
        self.context_window = 30720
        self.ttft_timeout = 2.0
        
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        chunks, budget = self._apply_token_budget(query, chunks)
        start = time.perf_counter()
        
        try:
            res = self.generator.generate(query, chunks, session_id, stream)
            if stream:
                async def stream_wrapper():
                    try:
                        iterator = res.__aiter__()
                        try:
                            first_chunk = await asyncio.wait_for(iterator.__anext__(), timeout=self.ttft_timeout)
                            yield first_chunk
                            self.record_success((time.perf_counter() - start) * 1000, 100)
                        except asyncio.TimeoutError:
                            raise TimeoutError(f"Gemini Time-To-First-Token exceeded ({self.ttft_timeout}s)")
                            
                        async for chunk in iterator:
                            yield chunk
                    except Exception as e:
                        self.record_failure(e)
                        raise
                return stream_wrapper()
            else:
                latency = (time.perf_counter() - start) * 1000
                self.record_success(latency, len(str(res))//4)
                return res
        except Exception as e:
            self.record_failure(e)
            raise


class OpenAIProviderStub(LLMProvider):
    def __init__(self):
        super().__init__(name="OpenAI", priority=3)
        self.is_active = False
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        raise NotImplementedError("OpenAI API credentials not configured.")


class ClaudeProviderStub(LLMProvider):
    def __init__(self):
        super().__init__(name="Claude", priority=4)
        self.is_active = False
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        raise NotImplementedError("Anthropic API credentials not configured.")


class ExtractiveFallbackProvider(LLMProvider):
    """Adapter for the Extractive generator."""
    def __init__(self):
        super().__init__(name="Extractive", priority=99)
        self.context_window = 10000
        
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        chunks, budget = self._apply_token_budget(query, chunks)
        start = time.perf_counter()
        try:
            from app.engines.extractive_composer import ExtractiveComposer
            gen = ExtractiveComposer()
            res = gen.generate(query, chunks, session_id, stream, response_plan)
            
            if stream:
                async def ext_stream():
                    yield res
                    self.record_success((time.perf_counter() - start) * 1000, len(res)//4)
                return ext_stream()
            else:
                self.record_success((time.perf_counter() - start) * 1000, len(res)//4)
                return res
        except Exception as e:
            self.record_failure(e)
            raise


class ProviderManager(AnswerGenerator):
    """Orchestrates multi-LLM routing with automatic failover."""
    
    def __init__(self):
        self.providers: list[LLMProvider] = [
            OllamaProvider(),
            GeminiProviderAdapter(),
            OpenAIProviderStub(),
            ClaudeProviderStub(),
            ExtractiveFallbackProvider()
        ]
        
    def add_provider(self, provider: LLMProvider):
        self.providers.append(provider)
        
    def get_all_metrics(self) -> list[dict[str, Any]]:
        return [p.get_metrics() for p in self.providers]
        
    def _get_active_providers(self) -> list[LLMProvider]:
        active = [p for p in self.providers if p.is_active and p.health_score >= 30.0]
        active.sort(key=lambda p: p.priority)
        return active
        
    def generate(self, query: str, chunks: list[dict[str, Any]], session_id: str | None = None, stream: bool = False, response_plan: Any = None) -> str | AsyncGenerator[str, None]:
        active_providers = self._get_active_providers()
        
        if not active_providers:
            logger.error("No healthy LLM providers available. Returning safe fallback.")
            msg = "The AI generation service is temporarily unavailable. Please refer to the source documents."
            if stream:
                async def safe_stream(): yield msg
                return safe_stream()
            return msg
            
        last_exception = None
        for provider in active_providers:
            logger.info(f"Attempting generation with provider: {provider.name}")
            try:
                res = provider.generate(query, chunks, session_id, stream, response_plan)
                return res
            except Exception as e:
                logger.warning(f"ProviderManager: {provider.name} failed with {e}. Failing over to next provider.")
                last_exception = e
                continue
                
        logger.error(f"ProviderManager: All providers failed. Last error: {last_exception}")
        msg = "An error occurred while generating the response. Please try again later."
        if stream:
            async def error_stream(): yield msg
            return error_stream()
        return msg
