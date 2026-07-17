"""Engine execution result model.

Defines the structure representing engine classification outcomes.
"""

from typing import Any

from pydantic import BaseModel, Field


class EngineResult(BaseModel):
    """Result returned by each conversation engine execution."""

    handled: bool
    reason_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
