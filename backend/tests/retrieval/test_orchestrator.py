import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.retrievers.retrieval_orchestrator import RetrievalOrchestrator

@pytest.mark.asyncio
async def test_orchestrator_execution_flow():
    """Verify the Orchestrator successfully chains the 10-stage pipeline without crashing."""
    session_mock = AsyncMock()
    
    with patch("app.engines.providers.factories.EntityProviderFactory.get_provider") as mock_entity_factory, \
         patch("app.engines.providers.factories.KeywordProviderFactory.get_provider") as mock_keyword_factory, \
         patch("app.engines.providers.factories.QueryRewriteProviderFactory.get_provider") as mock_rewrite_factory, \
         patch("app.engines.providers.factories.RerankerProviderFactory.get_provider") as mock_reranker_factory, \
         patch("app.retrievers.hybrid_retriever.HybridRetriever.retrieve", new_callable=AsyncMock) as mock_hybrid, \
         patch("app.engines.reranking.evidence_gate.EvidenceGate.filter_and_expand", new_callable=AsyncMock) as mock_evidence:
         
        mock_rewrite = AsyncMock()
        mock_rewrite.rewrite.return_value = "rewritten query"
        mock_rewrite_factory.return_value = mock_rewrite
        
        mock_hybrid.return_value = [{"chunk_id": "1"}]
        mock_evidence.return_value = [{"chunk_id": "1", "chunk": MagicMock()}]
        
        result = await RetrievalOrchestrator.execute(session_mock, "What is the policy?", [])
        
        assert result.trace_id is not None
        assert result.confidence in ["LOW", "MEDIUM", "HIGH"]
        assert "total_duration_ms" in result.metrics
        assert result.original_query == "What is the policy?"
