"""Strongly Typed DTO Layer for the Enterprise Generation Pipeline.

Every data payload passed between generation stages must use these dataclasses 
to ensure strict typing, observability, and avoid dictionary drift.
"""

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from app.database.models import DocumentChunk
from app.retrievers.retrieval_orchestrator import RetrievalResult


@dataclass
class GenerationEvidence:
    """Represents a validated and deduplicated chunk of evidence."""
    id: str
    text: str
    metadata: dict[str, Any]
    source_chunk: DocumentChunk
    relevance_score: float
    token_count: int
    semantic_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0


@dataclass
class GenerationContext:
    """The complete context payload sent downstream."""
    evidence: list[GenerationEvidence]
    total_tokens: int
    is_compressed: bool = False
    original_tokens: int = 0
    chunks_removed: int = 0
    sentences_removed: int = 0


@dataclass
class ResponsePlan:
    """The structural blueprint for the final response."""
    intent: str
    format_type: str  # e.g., Definition, Comparison, Markdown Table
    sections: list[str]
    token_budget: int
    max_words: int
    max_chunks: int
    temperature: float
    requires_citations: bool
    stream: bool
    compression_level: str
    allow_markdown: bool
    requires_safety_disclaimer: bool
    greeting_matched: bool = False


@dataclass
class PromptBundle:
    """The fully assembled prompt payload for the LLM."""
    system_prompt: str
    user_prompt: str
    context_text: str
    formatting_instructions: str


@dataclass
class ExtractiveDraft:
    """The deterministic, fact-only algorithmic draft answer."""
    content: str
    sentences: list[str]
    fully_supported: bool


@dataclass
class CitationReference:
    """Links a sentence to a specific chunk."""
    sentence_index: int
    chunk_id: str
    confidence: float
    document_name: str
    page_number: int


@dataclass
class CitationMap:
    """Collection of all citations for the response."""
    references: list[CitationReference]


@dataclass
class GenerationMetrics:
    """Tracks latency, token usage, and pipeline health."""
    durations_ms: dict[str, int] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    compression_ratio: float = 0.0
    evidence_count: int = 0
    citation_count: int = 0
    hallucination_count: int = 0
    llm_used: str = ""
    estimated_cost: float = 0.0


@dataclass
class GenerationState:
    """Holds pipeline execution state for logging and state-machine tracking."""
    trace_id: str
    current_status: str
    retrieval_result: RetrievalResult
    context: GenerationContext | None = None
    plan: ResponsePlan | None = None
    draft: ExtractiveDraft | None = None
    citations: CitationMap | None = None
    metrics: GenerationMetrics = field(default_factory=GenerationMetrics)


@dataclass
class FormattedResponse:
    """The response after markdown formatting and callout injections."""
    markdown_content: str
    has_broken_formatting: bool = False


@dataclass
class StreamChunk:
    """A discrete token or string chunk to be streamed to the client."""
    content: str
    is_done: bool


@dataclass
class FinalResponse:
    """The ultimate generation payload returned by the Orchestrator (if not streaming)."""
    trace_id: str
    content: str
    citations: list[dict[str, Any]]
    metrics: dict[str, Any]
    stream: AsyncGenerator[StreamChunk, None] | None = None
