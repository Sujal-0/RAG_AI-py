"""Pipeline executor unit tests."""

from app.pipeline.base import BaseEngine
from app.pipeline.context import ConversationContext
from app.pipeline.executor import run_pipeline
from app.pipeline.pipeline import PIPELINE
from app.pipeline.result import EngineResult


class MockEngine(BaseEngine):
    """Simple mock engine class for testing early stop scenarios."""

    def __init__(self, name: str, handled: bool, reason: str) -> None:
        self._name = name
        self.handled = handled
        self.reason = reason

    def execute(self, context: ConversationContext) -> EngineResult:
        if self.handled:
            context.response = f"Handled by {self._name}"
        return EngineResult(handled=self.handled, reason_code=self.reason)

    @property
    def name(self) -> str:
        return self._name


def test_pipeline_order() -> None:
    """Verify that the engine instances in the PIPELINE tuple match expected execution order."""
    expected_order = [
        "Validation",
        "Normalization",
        "EmptyInput",
        "Alias",
        "QueryDecision",
        "Greeting",
        "Goodbye",
        "Thanks",
        "SmallTalk",
        "QueryUnderstanding",
        "KnowledgeRetrieval",
        "RAGRetrieval",
        "Gibberish",
        "Fallback",
    ]
    actual_order = [engine.name for engine in PIPELINE]
    assert actual_order == expected_order


def test_pipeline_executor_runs_until_handled(monkeypatch) -> None:
    """Test that executor loops through engines and halts immediately when handled=True is returned."""
    # Define a custom pipeline list of mock engines
    custom_pipeline = (
        MockEngine("FirstEngine", handled=False, reason="FIRST_PASS"),
        MockEngine("SecondEngine", handled=True, reason="STOP_HERE"),
        MockEngine("ThirdEngine", handled=False, reason="SHOULD_NOT_RUN"),
    )

    # Monkeypatch the PIPELINE in executor/pipeline to use our mock sequence
    monkeypatch.setattr("app.pipeline.executor.PIPELINE", custom_pipeline)

    ctx = ConversationContext(
        request_id="req-test",
        session_id="sess-test-session",
        original_query="hello",
    )

    processed_ctx = run_pipeline(ctx)

    # Check outcome
    assert processed_ctx.response == "Handled by SecondEngine"

    # Verify trace entries
    assert len(processed_ctx.trace) == 2
    assert processed_ctx.trace[0]["engine"] == "FirstEngine"
    assert processed_ctx.trace[0]["handled"] is False
    assert processed_ctx.trace[0]["reasonCode"] == "FIRST_PASS"
    assert isinstance(processed_ctx.trace[0]["executionTimeMs"], float)

    assert processed_ctx.trace[1]["engine"] == "SecondEngine"
    assert processed_ctx.trace[1]["handled"] is True
    assert processed_ctx.trace[1]["reasonCode"] == "STOP_HERE"
