import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.pipeline.process import process_query
from app.repositories.document_repository import DocumentRepository

@pytest.fixture(autouse=True)
def mock_external_dependencies():
    with patch("app.repositories.document_repository.DocumentRepository.vector_search", new_callable=AsyncMock) as mock_vector, \
         patch("app.repositories.document_repository.DocumentRepository.hybrid_search", new_callable=AsyncMock) as mock_search, \
         patch("app.engines.llm_generator.GeminiAnswerGenerator.generate", new_callable=MagicMock) as mock_llm:
         
        mock_search.return_value = [
            {
                "chunk_id": "test-chunk-1",
                "text": "Mobiloitte is a company. The company mission is to provide AI services. Leave policy is generous. They are located in India.", 
                "filename": "about.pdf", 
                "page_number": 1, 
                "score": 0.9,
                "similarity": 0.9,
                "evidence_score": 0.9,
                "retrieval_method": "vector"
            }
        ]
        mock_vector.return_value = mock_search.return_value
        
        def fake_llm(*args, **kwargs):
            if kwargs.get("stream", False):
                async def gen():
                    yield "The company mission is to provide AI services."
                return gen()
            return "The company mission is to provide AI services."
            
        mock_llm.side_effect = fake_llm
        
        yield

def test_greeting_mixed_query():
    res = process_query(original_query="Hi tell me company mission", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] not in ("GREETING", "FALLBACK", "UNKNOWN")
    assert "tell me company mission" in (res.get("resolvedQuery") or "").lower()

def test_follow_up():
    from app.utils.session import SessionStore
    SessionStore.get_state("test_session_2").active_topic = "Company Info"
    res = process_query(original_query="tell me more", session_id="test_session_2", request_id="test_req")
    assert res["success"] is True
    assert res.get("resolvedQuery") != "tell me more"

def test_pronouns():
    from app.utils.session import SessionStore
    SessionStore.get_state("test_session_3").active_topic = "Offices"
    res = process_query(original_query="Where are they located?", session_id="test_session_3", request_id="test_req")
    assert res["success"] is True
    assert res.get("resolvedQuery") != "Where are they located?"

def test_leave_policy():
    res = process_query(original_query="Leave Policy", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] not in ("FALLBACK", "UNKNOWN")

def test_mission():
    res = process_query(original_query="Mission", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] not in ("FALLBACK", "UNKNOWN")

def test_services():
    res = process_query(original_query="Services", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] not in ("FALLBACK", "UNKNOWN")

def test_projects():
    res = process_query(original_query="Projects", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] not in ("FALLBACK", "UNKNOWN")

def test_multi_intent():
    res = process_query(original_query="Mission and Services", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] not in ("FALLBACK", "UNKNOWN")

def test_greeting_only():
    res = process_query(original_query="Hi", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] == "GREETING"

def test_unknown_query():
    # To test unknown query, we need hybrid search to return empty
    DocumentRepository.vector_search.return_value = []
    DocumentRepository.hybrid_search.return_value = []
    res = process_query(original_query="tell me about mars rovers", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] == "FALLBACK"
    assert "i don't have information" in res.get("answer", "").lower()

def test_database_exception_and_recovery():
    # 1. Database fails
    DocumentRepository.vector_search.side_effect = Exception("This session is provisioning a new connection; concurrent operations are not permitted")
    DocumentRepository.hybrid_search.side_effect = Exception("This session is provisioning a new connection; concurrent operations are not permitted")
    res = process_query(original_query="Tell me about leave policy", session_id="test_session", request_id="test_req")
    assert res["success"] is True
    assert res["intent"] == "DATABASE_FAILURE"
    assert "experiencing issues" in res.get("answer", "").lower()

    # 2. Database recovers
    DocumentRepository.vector_search.side_effect = None
    DocumentRepository.hybrid_search.side_effect = None
    DocumentRepository.vector_search.return_value = [
            {
                "chunk_id": "test-chunk-1",
                "text": "Leave policy is generous.", 
                "filename": "about.pdf", 
                "page_number": 1, 
                "score": 0.9,
                "similarity": 0.9,
                "evidence_score": 0.9,
                "retrieval_method": "vector"
            }
        ]
    res2 = process_query(original_query="Tell me about leave policy", session_id="test_session", request_id="test_req")
    assert res2["success"] is True
    assert res2["intent"] not in ("DATABASE_FAILURE", "FALLBACK", "UNKNOWN")

