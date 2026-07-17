import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.generation.orchestrator.generation_orchestrator import GenerationOrchestrator
from app.retrievers.retrieval_orchestrator import RetrievalResult
from app.engines.query.query_analyzer import NormalizedQuery
from app.engines.query.strategy_engine import RetrievalStrategy

@pytest.mark.asyncio
async def test_generation_pipeline_execution():
    """Verify GenerationOrchestrator successfully chains the 16-stage pipeline."""
    
    # Mock input RetrievalResult
    mock_retrieval = RetrievalResult(
        trace_id="test-trace-123",
        original_query="What is the policy?",
        normalized_query=NormalizedQuery(normalized_text="what is the policy", language="en", is_question=True, response_expectation="standard"),
        rewritten_query="What is the policy?",
        intent="Policy",
        strategy=RetrievalStrategy("Default", 0.7, 0.3, False, ["text"], False, 20),
        evidence=[], # Empty evidence should trigger Hallucination / Empty state
        confidence="LOW",
        confidence_score=0.0,
        metrics={}
    )
    
    # We don't need to patch the internal generation engines since they are built to be robust 
    # and handle empty evidence gracefully via ExtractiveComposer returning a safety fallback string.
    
    result = await GenerationOrchestrator.generate(mock_retrieval)
    
    assert result.trace_id == "test-trace-123"
    assert "metrics" in result.metrics
    # The ExtractiveComposer outputs a safety string when evidence is empty
    assert "knowledge base does not contain enough information" in result.content
