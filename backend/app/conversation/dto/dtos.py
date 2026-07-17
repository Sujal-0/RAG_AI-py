"""Strongly Typed DTO Layer for Conversation Intelligence."""

from dataclasses import dataclass, field
from typing import Any, List, Optional
import uuid

@dataclass
class ConversationEvent:
    event_type: str
    trace_id: str
    payload: dict[str, Any]

@dataclass
class ExecutionPlan:
    skip_retrieval: bool = False
    need_clarification: bool = False
    need_cache: bool = False
    need_multi_query: bool = False
    need_generation: bool = True
    need_streaming: bool = True
    need_tool: bool = False
    need_citation: bool = True
    clarification_message: str = ""
    target_strategy: str = "Standard"

@dataclass
class WorkingMemory:
    current_task: str = ""
    current_entities: list[str] = field(default_factory=list)
    current_files: list[str] = field(default_factory=list)
    current_goal: str = ""
    current_references: list[str] = field(default_factory=list)

@dataclass
class ConversationSession:
    session_id: str
    trace_id: str
    mode: str
    working_memory: WorkingMemory = field(default_factory=WorkingMemory)
    short_memory: list[dict] = field(default_factory=list)
    pinned_memory: list[dict] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

@dataclass
class ConversationMetrics:
    duration_ms: dict[str, int] = field(default_factory=dict)
    memory_usage: int = 0
    cache_hits: int = 0
    retrieval_skipped: bool = False
    llm_calls: int = 0
    token_budget: int = 0
    confidence: float = 0.0

@dataclass
class FinalConversationResponse:
    trace_id: str
    content: str
    citations: list[dict] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    is_clarification: bool = False
