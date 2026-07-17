"""Generation Orchestrator.

The sole public entry point for the Enterprise Generation Pipeline.
Wires the DTOs and state machine through the 16 functional components.
"""

import logging
import time
from typing import AsyncGenerator

from app.core.settings import settings
from app.retrievers.retrieval_orchestrator import RetrievalResult
from app.generation.dto.dtos import GenerationState, GenerationMetrics, FinalResponse, StreamChunk
from app.generation.orchestrator.state_machine import GenerationStateMachine, GenerationStatus

from app.generation.builders.context_builder import ContextBuilder
from app.generation.builders.window_manager import ContextWindowManager
from app.generation.builders.context_compressor import ContextCompressor
from app.generation.builders.response_planner import ResponsePlanner
from app.generation.builders.prompt_builder import PromptBuilder

from app.generation.validators.evidence_validator import EvidenceValidator
from app.generation.validators.hallucination_engine import HallucinationEngine
from app.generation.validators.quality_engine import ResponseQualityEngine

from app.generation.engines.extractive_composer import ExtractiveComposer
from app.generation.engines.citation_engine import CitationEngine
from app.generation.engines.llm_enhancer import LLMEnhancerProviderFactory
from app.generation.formatters.markdown_formatter import FormatterProviderFactory
from app.generation.streaming.stream_controller import StreamingProviderFactory

logger = logging.getLogger("app")


class GenerationOrchestrator:
    """Coordinates the deterministic extraction and enhancement pipeline."""
    
    @classmethod
    async def generate(cls, retrieval_result: RetrievalResult) -> FinalResponse:
        """Execute the full generation pipeline using strictly typed DTOs."""
        
        trace_id = retrieval_result.trace_id
        start_time = time.time()
        
        state = GenerationState(
            trace_id=trace_id,
            current_status="INITIALIZING",
            retrieval_result=retrieval_result,
            metrics=GenerationMetrics()
        )
        
        logger.info(
            "Starting Generation Pipeline",
            extra={"structured_log": True, "trace_id": trace_id, "stage": "GenerationOrchestrator"}
        )

        try:
            # Step 1: Context Builder
            GenerationStateMachine.transition(state, GenerationStatus.BUILD_CONTEXT)
            state.context = ContextBuilder.build(retrieval_result.evidence)
            
            # Step 2: Context Window Manager
            GenerationStateMachine.transition(state, GenerationStatus.WINDOW_SELECTION)
            state.context = ContextWindowManager.select(state.context)
            
            # Step 3: Context Compression
            GenerationStateMachine.transition(state, GenerationStatus.COMPRESS_CONTEXT)
            state.context = ContextCompressor.compress(state.context)
            
            # Step 4: Evidence Validation & Coverage
            GenerationStateMachine.transition(state, GenerationStatus.VALIDATE_EVIDENCE)
            state.context = EvidenceValidator.validate(state.context)
            
            # Step 5: Response Planner
            GenerationStateMachine.transition(state, GenerationStatus.PLAN_RESPONSE)
            state.plan = ResponsePlanner.plan(retrieval_result.intent)
            
            # Step 6: Extractive Composer
            GenerationStateMachine.transition(state, GenerationStatus.GENERATE_DRAFT)
            state.draft = ExtractiveComposer.draft(state.context, state.plan)
            
            # Step 7: Citation Engine
            GenerationStateMachine.transition(state, GenerationStatus.GENERATE_CITATIONS)
            state.citations = CitationEngine.map_citations(state.draft, state.context)
            
            # Step 8: Hallucination Guard
            GenerationStateMachine.transition(state, GenerationStatus.VERIFY_RESPONSE)
            is_safe = HallucinationEngine.verify(state.draft, state.context, state.citations)
            
            if not is_safe and settings.generation.hallucination_tolerance == "zero":
                # Severe fallback
                state.draft.content = "I'm sorry, I could not verify the facts in the retrieved context to answer this query safely."
            
            # Step 9: Build Prompt & LLM Enhancement
            GenerationStateMachine.transition(state, GenerationStatus.BUILD_PROMPT)
            prompt_bundle = PromptBuilder.build(state.draft, state.plan)
            
            GenerationStateMachine.transition(state, GenerationStatus.POLISH_RESPONSE)
            enhancer = LLMEnhancerProviderFactory.get_provider(settings.generation.llm_enhancer_provider)
            polished_content = await enhancer.polish(state.draft, prompt_bundle, state.plan)
            
            # Step 10: Response Formatter
            GenerationStateMachine.transition(state, GenerationStatus.FORMAT_RESPONSE)
            formatter = FormatterProviderFactory.get_provider(settings.generation.formatter_provider)
            formatted_response = formatter.format(polished_content, state.plan)
            
            # Step 11: Quality Check
            GenerationStateMachine.transition(state, GenerationStatus.QUALITY_CHECK)
            final_formatted = ResponseQualityEngine.check_and_repair(formatted_response)
            
            # Step 12: Streaming (Optional)
            GenerationStateMachine.transition(state, GenerationStatus.STREAM_RESPONSE)
            streamer = StreamingProviderFactory.get_provider(settings.generation.streaming_provider)
            stream_gen = streamer.stream(final_formatted)
            
            GenerationStateMachine.transition(state, GenerationStatus.COMPLETE)
            
            # --- Populate Final Metrics ---
            state.metrics.durations_ms["total_generation_ms"] = int((time.time() - start_time) * 1000)
            state.metrics.evidence_count = len(state.context.evidence)
            state.metrics.citation_count = len(state.citations.references) if state.citations else 0
            state.metrics.llm_used = settings.generation.llm_enhancer_provider
            state.metrics.compression_ratio = round(
                state.context.total_tokens / max(sum(e.token_count for e in retrieval_result.evidence), 1), 2
            ) if retrieval_result.evidence else 0.0
            
            logger.info(
                "Generation Pipeline Complete",
                extra={"structured_log": True, "trace_id": trace_id, "metrics": state.metrics.__dict__}
            )
            
            return FinalResponse(
                trace_id=trace_id,
                content=final_formatted.markdown_content,
                citations=[ref.__dict__ for ref in state.citations.references] if state.citations else [],
                metrics=state.metrics.__dict__,
                stream=stream_gen
            )

        except Exception as e:
            GenerationStateMachine.transition(state, GenerationStatus.FAILED)
            logger.error(
                f"Generation Pipeline Failed: {e}",
                extra={"structured_log": True, "trace_id": trace_id, "stage": "GenerationOrchestrator"},
                exc_info=True
            )
            raise
