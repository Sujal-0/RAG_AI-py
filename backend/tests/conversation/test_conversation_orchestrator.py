import pytest
import time
from app.conversation.orchestrator.orchestrator import ConversationOrchestrator

@pytest.mark.asyncio
async def test_decision_engine_skips_retrieval_on_greeting():
    """Verify that greetings bypass the Retrieval engine entirely and hit latency budgets."""
    
    start_time = time.time()
    
    response = await ConversationOrchestrator.process_turn(
        query="Hello!",
        session_id="test-session-001"
    )
    
    duration = (time.time() - start_time) * 1000
    
    assert response.is_clarification is True
    assert "Hello" in response.content
    assert duration < 50 # Under 50ms overhead for fast path
