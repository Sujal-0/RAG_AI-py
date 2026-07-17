"""Conversation Modes.

Determines the operational persona and strictness of the Pipeline.
Modifies TopK, Generation strictness, and Memory configurations implicitly.
"""

import logging
from dataclasses import dataclass

from app.core.settings import settings

logger = logging.getLogger("app")


@dataclass
class ConversationModeConfig:
    mode_name: str
    hallucination_tolerance: str
    requires_citations: bool
    context_budget_multiplier: float


class ConversationModeEngine:
    """Manages conversational modes (e.g., Coding vs Research)."""
    
    MODES = {
        "General Chat": ConversationModeConfig("General Chat", "low", False, 1.0),
        "Research": ConversationModeConfig("Research", "zero", True, 1.5),
        "Coding": ConversationModeConfig("Coding", "zero", False, 1.2),
        "Architecture": ConversationModeConfig("Architecture", "zero", True, 2.0)
    }
    
    @classmethod
    def get_mode_config(cls, mode_name: str) -> ConversationModeConfig:
        logger.info(f"Loading Conversation Mode: {mode_name}", extra={"structured_log": True, "stage": "ModeEngine"})
        return cls.MODES.get(mode_name, cls.MODES["General Chat"])
