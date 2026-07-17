"""Integration tests for Phase 6 Final Stabilization RAG pipeline."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.engines.rag_engine import RAGEngine, RuleBasedAnswerGenerator
from app.pipeline.context import ConversationContext
from app.pipeline.process import process_query
from app.utils.session import SessionStore
from app.api.chat import ChatRequest
from app.main import app

client = TestClient(app)


def test_rule_based_answer_generator_multi_topic_merging() -> None:
    """Verify RuleBasedAnswerGenerator merges multiple topics/documents together."""
    generator = RuleBasedAnswerGenerator()
    chunks = [
        {
            "score": 0.95,
            "filename": "Security_Policy.pdf",
            "page_number": 2,
            "chunk_id": "sec-1",
            "text": "All employee laptops must use VPN when accessing AWS.",
            "version_number": 1,
        },
        {
            "score": 0.92,
            "filename": "Leave_Policy.pdf",
            "page_number": 1,
            "chunk_id": "leave-1",
            "text": "Annual leave must be requested 2 weeks in advance.",
            "version_number": 1,
        }
    ]
    query = "Security Policy and Leave Policy"
    response = generator.generate(query, chunks)

    assert "According to the uploaded documents:" in response
    assert "From Security_Policy.pdf:" in response
    assert "From Leave_Policy.pdf:" in response
    assert "Security_Policy.pdf (Page 2)" in response
    assert "Leave_Policy.pdf (Page 1)" in response


@pytest.mark.anyio
async def test_rag_pipeline_ordering_and_fallback() -> None:
    """Verify RAG engine runs and when no match is found, pipeline falls back."""
    SessionStore.clear()
    
    # 1. No match above threshold: handled=False, goes to fallback
    context = ConversationContext(
        request_id="req-test-ordering",
        session_id="session-ordering-1",
        original_query="What is Kubernetes architecture?",
    )
    
    engine = RAGEngine()
    
    with patch("app.embeddings.embedding_service.EmbeddingService.generate_embedding", return_value=[0.1]*384), \
         patch("app.repositories.document_repository.DocumentRepository.vector_search", return_value=[]):
        
        result = engine.execute(context)
        assert result.handled is False
        assert result.reason_code == "RAG_NO_RELEVANT_CHUNKS"
        assert context.response is None


def test_chat_api_with_custom_similarity_threshold() -> None:
    """Verify chat API accepts similarityThreshold payload and processes query successfully."""
    # Mock process_query to assert similarity_threshold metadata is passed correctly
    with patch("app.api.chat.process_query") as mock_process:
        mock_process.return_value = {"success": True, "answer": "Stubbed response"}
        
        response = client.post(
            "/api/v1/chat",
            json={
                "query": "What is the AWS policy?",
                "sessionId": "session-custom-thresh-123",
                "similarityThreshold": 0.55
            }
        )
        assert response.status_code == 200
        
        # Verify custom similarity threshold was passed as metadata to process_query
        assert mock_process.call_count == 1
        _, kwargs = mock_process.call_args
        assert kwargs["original_query"] == "What is the AWS policy?"
        assert kwargs["session_id"] == "session-custom-thresh-123"
        assert kwargs["metadata"] == {"similarity_threshold": 0.55}


@pytest.mark.anyio
async def test_rag_pipeline_telemetry_fields() -> None:
    """Verify RAG engine execute stashes detailed telemetry metadata."""
    SessionStore.clear()
    
    mock_chunks = [
        {
            "score": 0.78,
            "filename": "Laptop_Policy.txt",
            "page_number": 1,
            "chunk_id": "txt-1",
            "text": "Laptops are replaced every 3 years.",
            "version_number": 1,
        }
    ]
    
    context = ConversationContext(
        request_id="req-telemetry-1",
        session_id="session-telemetry-1",
        original_query="How often are laptops replaced?",
    )
    
    engine = RAGEngine()
    
    with patch("app.embeddings.embedding_service.EmbeddingService.generate_embedding", return_value=[0.2]*384), \
         patch("app.repositories.document_repository.DocumentRepository.vector_search", return_value=mock_chunks):
        
        result = engine.execute(context)
        
        assert result.handled is True
        # Telemetry fields
        assert "similarityScore" in result.metadata
        assert "chunkCount" in result.metadata
        assert "documentsUsed" in result.metadata
        assert "searchTimeMs" in result.metadata
        assert "embeddingTimeMs" in result.metadata
        assert "retrievedChunks" in result.metadata
        assert result.metadata["similarityScore"] == 0.78
        assert result.metadata["chunkCount"] == 1
        assert result.metadata["documentsUsed"] == ["Laptop_Policy.txt"]
        assert len(result.metadata["retrievedChunks"]) == 1
        assert result.metadata["retrievedChunks"][0]["filename"] == "Laptop_Policy.txt"
        assert result.metadata["retrievedChunks"][0]["pageNumber"] == 1
        assert result.metadata["retrievedChunks"][0]["chunkId"] == "txt-1"
