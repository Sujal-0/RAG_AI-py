"""Chat endpoint integration tests."""

from fastapi.testclient import TestClient


def test_chat_returns_correct_response_format(client: TestClient) -> None:
    """POST /api/v1/chat with valid payload returns placeholder fallback response."""
    payload = {"query": "what is the stock price", "sessionId": "sess-valid-12345"}
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "FALLBACK"
    assert "I don't have information about that." in data["answer"]
    assert data["reasonCode"] == "FALLBACK_HELPFUL_OUTCOME"
    assert "requestId" in data
    assert data["normalizedQuery"] == "what is the stock price"
    assert "timestamp" in data
    assert isinstance(data["metadata"], dict)

    # Check trace structure is present inside metadata
    trace = data["metadata"]["trace"]
    assert isinstance(trace, list)
    assert len(trace) == 14  # All 14 engines execute in sequence
    assert trace[-1]["engine"] == "Fallback"
    assert trace[-1]["handled"] is True


def test_chat_validation_missing_fields(client: TestClient) -> None:
    """POST /api/v1/chat with missing query or sessionId fails with 422."""
    response = client.post("/api/v1/chat", json={"query": "hello"})
    assert response.status_code == 422

    response = client.post("/api/v1/chat", json={"sessionId": "sess-1234"})
    assert response.status_code == 422


def test_chat_validation_invalid_session_id(client: TestClient) -> None:
    """POST /api/v1/chat with malformed sessionId fails with 422 validation error."""
    payload = {
        "query": "hello",
        "sessionId": "sess-invalid-id-with-special-char-@",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


def test_chat_validation_too_long_query(client: TestClient) -> None:
    """POST /api/v1/chat with query exceeding 1000 characters fails with 422."""
    payload = {"query": "a" * 1001, "sessionId": "sess-valid"}
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


def test_debug_pipeline_endpoint(client: TestClient) -> None:
    """GET /api/v1/debug/pipeline returns list of engine names."""
    response = client.get("/api/v1/debug/pipeline")
    assert response.status_code == 200

    data = response.json()
    assert data["debug"] is True
    assert data["totalEnginesCount"] == 14
    assert "Validation" in data["engineOrder"]
    assert "Fallback" in data["engineOrder"]
