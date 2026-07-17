"""ConversationContext unit tests."""

from datetime import datetime

from app.pipeline.context import ConversationContext


def test_context_creation() -> None:
    """Test creating a ConversationContext instance with valid fields."""
    ctx = ConversationContext(
        request_id="req-123",
        session_id="sess-12345678",
        original_query="hello",
    )
    assert ctx.request_id == "req-123"
    assert ctx.session_id == "sess-12345678"
    assert ctx.original_query == "hello"
    assert ctx.normalized_query is None
    assert ctx.tokens == []
    assert ctx.intent is None
    assert ctx.response is None
    assert ctx.metadata == {}
    assert ctx.trace == []
    assert isinstance(ctx.timestamp, str)
    # Verify ISO 8601 format by parsing
    parsed_dt = datetime.fromisoformat(ctx.timestamp.replace("Z", "+00:00"))
    assert parsed_dt is not None


def test_context_mutation() -> None:
    """Test mutating fields of the context model."""
    ctx = ConversationContext(
        request_id="req-123",
        session_id="sess-12345678",
        original_query="hello",
    )
    ctx.normalized_query = "hello"
    ctx.tokens = ["hello"]
    ctx.intent = "GREETING"
    ctx.response = "Hi there!"
    ctx.metadata["flag"] = True
    ctx.trace.append({"engine": "Greeting", "handled": True})

    assert ctx.normalized_query == "hello"
    assert ctx.tokens == ["hello"]
    assert ctx.intent == "GREETING"
    assert ctx.response == "Hi there!"
    assert ctx.metadata["flag"] is True
    assert len(ctx.trace) == 1
    assert ctx.trace[0]["engine"] == "Greeting"


def test_context_serialization() -> None:
    """Test context serialization to JSON-compatible dictionary."""
    ctx = ConversationContext(
        request_id="req-123",
        session_id="sess-12345678",
        original_query="hello",
    )
    serialized = ctx.model_dump()
    assert isinstance(serialized, dict)
    assert serialized["request_id"] == "req-123"
    assert serialized["session_id"] == "sess-12345678"
    assert serialized["original_query"] == "hello"
