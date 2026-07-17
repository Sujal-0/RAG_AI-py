"""Abstract base engine contract.

Defines the interface all processing engines must implement.
"""

from abc import ABC, abstractmethod

from app.pipeline.context import ConversationContext
from app.pipeline.result import EngineResult


class BaseEngine(ABC):
    """Abstract Base Class for all pipeline engines."""

    @abstractmethod
    def execute(self, context: ConversationContext) -> EngineResult:
        """Execute the engine's deterministic classification logic.

        Args:
            context: Active conversation context state.

        Returns:
            EngineResult representing outcome (handled, reason_code, metadata).
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name identifier of the engine."""
        pass
