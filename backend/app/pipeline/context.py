"""Conversation context model.

Defines the structure for carrying transaction state through the pipeline.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.pipeline.intents import Intent


class ConversationContext(BaseModel):
    """Execution context containing query data and pipeline state."""

    request_id: str
    session_id: str
    original_query: str
    raw_query: str | None = None
    normalized_query: str | None = None
    remaining_query: str | None = None
    resolved_query: str | None = None
    expanded_query: str | None = None
    tokens: list[str] = Field(default_factory=list)
    intent: Intent | str | None = None
    response: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="before")
    @classmethod
    def populate_raw_query(cls, data: Any) -> Any:
        """Populate raw_query automatically from original_query if not provided."""
        if isinstance(data, dict) and data.get("raw_query") is None:
            data["raw_query"] = data.get("original_query")
        return data
