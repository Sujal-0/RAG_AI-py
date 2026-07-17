"""Integration tests for Phase 6B RAG Retrieval & Conversation memory."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.engines.rag_engine import RAGEngine, RuleBasedAnswerGenerator
from app.pipeline.context import ConversationContext
from app.pipeline.process import process_query
from app.utils.session import SessionStore


def test_rule_based_answer_generator_single_doc() -> None:
    """Verify that RuleBasedAnswerGenerator summarizes a single doc and formats citations."""
    generator = RuleBasedAnswerGenerator()
    chunks = [
        {
            "score": 0.95,
            "filename": "Employee_Handbook.pdf",
            "page_number": 4,
            "chunk_id": "c-1",
            "text": "MFA is mandatory for all access. Zero Trust is enforced. Please use authenticated portals.",
            "version_number": 1,
        },
        {
            "score": 0.88,
            "filename": "Employee_Handbook.pdf",
            "page_number": 4,
            "chunk_id": "c-2",
            "text": "Sick leave requires a medical certificate if extending beyond two working days.",
            "version_number": 1,
        }
    ]
    query = "MFA Zero Trust sick leave"
    response = generator.generate(query, chunks)
    
    assert "According to the uploaded Employee_Handbook.pdf (v1):" in response
    assert "MFA is mandatory" in response
    assert "Sick leave requires" in response
    assert "(Source: Employee_Handbook.pdf — Page 4)" in response


def test_rule_based_answer_generator_multi_doc() -> None:
    """Verify multi-document summary generation when scores are close."""
    generator = RuleBasedAnswerGenerator()
    chunks = [
        {
            "score": 0.92,
            "filename": "Company_Vision.md",
            "page_number": 1,
            "chunk_id": "vision-1",
            "text": "Our vision is to empower global organizations using innovative AI technologies.",
            "version_number": 1,
        },
        {
            "score": 0.90,
            "filename": "Company_Mission.md",
            "page_number": 2,
            "chunk_id": "mission-1",
            "text": "Our mission is to deliver high-quality engineering services consistently.",
            "version_number": 1,
        }
    ]
    query = "vision and mission"
    response = generator.generate(query, chunks)
    
    assert "According to the uploaded documents:" in response
    assert "From Company_Vision.md:" in response
    assert "From Company_Mission.md:" in response
    assert "Company_Vision.md (Page 1)" in response
    assert "Company_Mission.md (Page 2)" in response


@pytest.mark.anyio
async def test_rag_engine_flow_success() -> None:
    """Verify RAGEngine retrieves chunks, scores them, and updates context successfully."""
    SessionStore.clear()
    
    mock_chunks = [
        {
            "score": 0.85,
            "filename": "Handbook.docx",
            "page_number": 3,
            "chunk_id": "ch-9",
            "text": "Probation period is 3 months. Reviews occur monthly.",
            "version_number": 1,
        }
    ]
    
    context = ConversationContext(
        request_id="req-123",
        session_id="session-rag-test",
        original_query="What is the probation period?",
    )
    
    engine = RAGEngine()
    
    with patch("app.embeddings.embedding_service.EmbeddingService.generate_embedding", return_value=[0.1]*384), \
         patch("app.repositories.document_repository.DocumentRepository.vector_search", return_value=mock_chunks):
        
        result = engine.execute(context)
        
        assert result.handled is True
        assert result.reason_code == "RAG_RETRIEVED_SUCCESSFULLY"
        assert context.intent == "KNOWLEDGE_RETRIEVED"
        assert "Probation period is 3 months" in context.response
        assert "(Source: Handbook.docx — Page 3)" in context.response
        
        # Telemetry verification
        assert "similarityScore" in result.metadata
        assert result.metadata["similarityScore"] == 0.85
        assert result.metadata["chunkCount"] == 1
        assert "Handbook.docx" in result.metadata["documentsUsed"]


@pytest.mark.anyio
async def test_rag_engine_flow_below_threshold() -> None:
    """Verify RAGEngine skips execution if similarity is below configured threshold."""
    SessionStore.clear()
    
    mock_chunks = [
        {
            "score": 0.25,  # below default 0.42
            "filename": "Handbook.docx",
            "page_number": 3,
            "chunk_id": "ch-9",
            "text": "Unrelated paragraph text about computer screens.",
            "version_number": 1,
        }
    ]
    
    context = ConversationContext(
        request_id="req-124",
        session_id="session-rag-test-2",
        original_query="What is probation?",
    )
    
    engine = RAGEngine()
    
    with patch("app.embeddings.embedding_service.EmbeddingService.generate_embedding", return_value=[0.1]*384), \
         patch("app.repositories.document_repository.DocumentRepository.vector_search", return_value=mock_chunks):
        
        result = engine.execute(context)
        
        assert result.handled is False
        assert result.reason_code == "RAG_NO_RELEVANT_CHUNKS"
        assert context.response is None


@pytest.mark.anyio
async def test_conversational_memory_follow_up() -> None:
    """Verify RAGEngine pulls previous session context chunks for follow-up queries."""
    SessionStore.clear()
    
    session_id = "session-follow-up-1"
    
    # Seed session store with previous context chunks
    cached_chunks = [
        {
            "score": 0.90,
            "filename": "Leave_Policy.pdf",
            "page_number": 1,
            "chunk_id": "c-99",
            "text": "Employees get 12 annual leaves and 8 sick leaves.",
            "version_number": 1,
        }
    ]
    SessionStore.set_last_context(session_id, "tell me about leaves", cached_chunks, "LEAVE_POLICY")
    
    context = ConversationContext(
        request_id="req-125",
        session_id=session_id,
        original_query="how many sick leaves?",
    )
    
    engine = RAGEngine()
    
    # Mock current vector search returning nothing above threshold
    with patch("app.embeddings.embedding_service.EmbeddingService.generate_embedding", return_value=[0.1]*384), \
         patch("app.repositories.document_repository.DocumentRepository.vector_search", return_value=[]):
        
        result = engine.execute(context)
        
        assert result.handled is True
        assert result.reason_code == "RAG_RETRIEVED_SUCCESSFULLY"
        assert "leaves and 8 sick leaves" in context.response
        assert "(Source: Leave_Policy.pdf — Page 1)" in context.response


def test_confidence_based_greeting_routing() -> None:
    """Verify greeting and business confidence comparison routing in build_response."""
    SessionStore.clear()
    
    # 1. Greeting dominates: Greeting returned only
    context1 = ConversationContext(request_id="r-1", session_id="s-1", original_query="hello")
    context1.metadata["greeting_prefix_key"] = "hello"
    # Greeting confidence = 1.0, business confidence = 0.0 (fallback / not handled)
    context1.metadata["greeting_confidence"] = 1.0
    context1.metadata["confidence"] = 0.0
    
    res1 = process_query("hello", "s-1", "r-1", metadata=context1.metadata)
    assert res1["intent"] == "GREETING"
    assert any(word in res1["answer"] for word in ["Hello", "Hi", "Hey", "Greetings"])
    
    # 2. Both meaningful: Natural concatenated response
    context2 = ConversationContext(request_id="r-2", session_id="s-2", original_query="hello career")
    context2.metadata["greeting_prefix_key"] = "hello"
    context2.metadata["greeting_confidence"] = 1.0
    context2.metadata["confidence"] = 0.95
    context2.response = "We have open roles in Noida."
    context2.intent = "CAREERS"
    
    # Stub pipeline logic execution
    with patch("app.pipeline.process.run_pipeline", return_value=context2):
        res2 = process_query("hello career", "s-2", "r-2", metadata=context2.metadata)
        assert res2["intent"] == "COMPANY_INTENT"
        assert res2["displayIntent"] == "Company Information"
        # Natural spacing paragraph split
        assert any(res2["answer"].startswith(p) for p in ["Hello", "Hi", "Hey", "Greetings"])
        assert res2["answer"].endswith("We have open roles in Noida.")
        assert "\n\n" in res2["answer"]
