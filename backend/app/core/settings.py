"""Application settings configuration.

Defines global parameters loaded from the environment using Pydantic Settings,
structured into logical configuration categories.
"""

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    """General application settings."""

    name: str
    version: str
    environment: str
    debug: bool


class DatabaseSettings(BaseModel):
    """Database configuration parameters."""

    url: str


class UploadSettings(BaseModel):
    """File upload and persistence settings."""

    directory: str
    max_file_size_mb: int


class EmbeddingSettings(BaseModel):
    """SentenceTransformer model configuration."""

    model: str
    dimension: int


class WorkerSettings(BaseModel):
    """Asynchronous background worker execution parameters."""

    concurrency: int


class VectorSearchSettings(BaseModel):
    """Semantic vector search defaults."""

    default_limit: int
    similarity_threshold: float
    reject_threshold: float
    weak_threshold: float
    strong_threshold: float



class RetrievalSettings(BaseModel):
    """Enterprise Retrieval Engine configurations."""
    
    # Enable/Disable flags
    metadata_filter_enabled: bool
    bm25_enabled: bool
    hybrid_enabled: bool
    context_compression_enabled: bool
    
    # Top K Limits
    top_k_dense: int
    top_k_sparse: int
    top_k_hybrid: int
    top_k_rerank: int
    
    # Weights and Constants
    dense_weight: float
    sparse_weight: float
    rrf_constant: int
    
    # Thresholds
    minimum_similarity: float
    weak_threshold: float
    strong_threshold: float
    query_rewrite_threshold: int
    followup_detection_threshold: int
    
    # Providers
    reranker_provider: str
    reranker_model: str
    entity_provider: str
    keyword_provider: str
    rewrite_provider: str
    
    # Operation Limits
    reranker_batch_size: int
    reranker_timeout: int
    retrieval_timeout: int
    maximum_context_tokens: int
    maximum_candidate_chunks: int
    minimum_chunk_size: int
    maximum_chunk_size: int
    retry_counts: int
    
    # Neighbors
    neighbor_expansion_enabled: bool
    maximum_neighbor_depth: int
    chunk_expansion_count: int


class GenerationSettings(BaseModel):
    """Enterprise Generation Engine configurations."""
    
    # Validation & Strictly Extractive Settings
    enforce_extractive_drafting: bool
    hallucination_tolerance: str  # e.g., 'zero', 'low'
    
    # Providers
    llm_enhancer_provider: str
    formatter_provider: str
    streaming_provider: str
    citation_provider: str
    compression_provider: str
    prompt_builder_provider: str
    quality_engine_provider: str
    
    # Operation Limits
    max_input_tokens: int
    max_output_tokens: int
    enhancer_timeout: int
    enhancer_retry_counts: int
    
    # Caching
    response_cache_enabled: bool
    response_cache_ttl: int


class ConversationSettings(BaseModel):
    """Enterprise Conversation Intelligence configurations."""
    
    # Feature Flags
    enable_multi_query: bool
    enable_caching: bool
    enable_streaming: bool
    enable_clarification: bool
    enable_neighbor_expansion: bool
    enable_reranker: bool
    enable_summaries: bool
    enable_memory: bool
    
    # Modes & Providers
    default_conversation_mode: str
    cache_provider: str
    memory_provider: str
    
    # Thresholds
    clarification_ambiguity_threshold: float
    summary_token_threshold: int
    max_context_turns: int
    working_memory_size: int

class LoggingSettings(BaseModel):
    """Logging structure and levels."""

    level: str
    format_str: str


class LlmSettings(BaseModel):
    """LLM configuration parameters."""

    provider: str
    model: str
    api_key: str | None


class ApiSettings(BaseModel):
    """API host and port configurations."""

    host: str
    port: int


class Settings(BaseSettings):
    """Root application settings manager.

    Loads, structures, and validates settings from environment variables or .env file.
    """

    # Flat variables mapped from environment/dotenv
    APP_NAME: str = "Mobiloitte AI Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = (
        "postgresql://postgres:postgres_password@localhost:5432/mobiloitte_ai"
    )

    UPLOAD_DIR: str = Field(
        "uploads", validation_alias=AliasChoices("UPLOAD_DIRECTORY", "UPLOAD_DIR")
    )
    MAX_FILE_SIZE_MB: int = 10

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    GEMINI_API_KEY: str | None = None
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3-flash-preview"
    
    OLLAMA_ENABLED: str = "true"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    OLLAMA_TIMEOUT: str = "30"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    WORKER_CONCURRENCY: int = 1
    VECTOR_SEARCH_LIMIT: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.42

    RAG_TOP_K: int = 10
    RAG_REJECT_THRESHOLD: float = 0.42
    RAG_WEAK_THRESHOLD: float = 0.74
    RAG_STRONG_THRESHOLD: float = 0.86

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "%(asctime)s [%(levelname)s] [Request:%(request_id)s] %(name)s: %(message)s"
    )

    # --- Enterprise Retrieval Settings ---
    RETRIEVAL_METADATA_FILTER_ENABLED: bool = True
    RETRIEVAL_BM25_ENABLED: bool = True
    RETRIEVAL_HYBRID_ENABLED: bool = True
    RETRIEVAL_CONTEXT_COMPRESSION_ENABLED: bool = False
    
    RETRIEVAL_TOP_K_DENSE: int = 40
    RETRIEVAL_TOP_K_SPARSE: int = 40
    RETRIEVAL_TOP_K_HYBRID: int = 40
    RETRIEVAL_TOP_K_RERANK: int = 5
    
    RETRIEVAL_DENSE_WEIGHT: float = 0.7
    RETRIEVAL_SPARSE_WEIGHT: float = 0.3
    RETRIEVAL_RRF_CONSTANT: int = 60
    
    RETRIEVAL_MINIMUM_SIMILARITY: float = 0.3
    RETRIEVAL_WEAK_THRESHOLD: float = -5.0
    RETRIEVAL_STRONG_THRESHOLD: float = 2.0
    RETRIEVAL_QUERY_REWRITE_THRESHOLD: int = 4
    RETRIEVAL_FOLLOWUP_DETECTION_THRESHOLD: int = 3
    
    RETRIEVAL_RERANKER_PROVIDER: str = "sentence_transformer"
    RETRIEVAL_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RETRIEVAL_ENTITY_PROVIDER: str = "spacy"
    RETRIEVAL_KEYWORD_PROVIDER: str = "heuristic"
    RETRIEVAL_REWRITE_PROVIDER: str = "heuristic"
    
    RETRIEVAL_RERANKER_BATCH_SIZE: int = 32
    RETRIEVAL_RERANKER_TIMEOUT: int = 15
    RETRIEVAL_TIMEOUT: int = 30
    RETRIEVAL_MAXIMUM_CONTEXT_TOKENS: int = 4000
    RETRIEVAL_MAXIMUM_CANDIDATE_CHUNKS: int = 100
    RETRIEVAL_MINIMUM_CHUNK_SIZE: int = 50
    RETRIEVAL_MAXIMUM_CHUNK_SIZE: int = 1500
    RETRIEVAL_RETRY_COUNTS: int = 3
    
    RETRIEVAL_NEIGHBOR_EXPANSION_ENABLED: bool = True
    RETRIEVAL_MAXIMUM_NEIGHBOR_DEPTH: int = 2
    RETRIEVAL_CHUNK_EXPANSION_COUNT: int = 2

    # --- Enterprise Generation Settings ---
    GENERATION_ENFORCE_EXTRACTIVE_DRAFTING: bool = True
    GENERATION_HALLUCINATION_TOLERANCE: str = "zero"
    GENERATION_LLM_ENHANCER_PROVIDER: str = "gemini"
    GENERATION_FORMATTER_PROVIDER: str = "markdown"
    GENERATION_STREAMING_PROVIDER: str = "sse"
    GENERATION_CITATION_PROVIDER: str = "default"
    GENERATION_COMPRESSION_PROVIDER: str = "algorithmic"
    GENERATION_PROMPT_BUILDER_PROVIDER: str = "default"
    GENERATION_QUALITY_ENGINE_PROVIDER: str = "default"
    GENERATION_MAX_INPUT_TOKENS: int = 8000
    GENERATION_MAX_OUTPUT_TOKENS: int = 2048
    GENERATION_ENHANCER_TIMEOUT: int = 45
    GENERATION_ENHANCER_RETRY_COUNTS: int = 2
    GENERATION_RESPONSE_CACHE_ENABLED: bool = False
    GENERATION_RESPONSE_CACHE_TTL: int = 3600

    # --- Enterprise Conversation Intelligence Settings ---
    CONVERSATION_ENABLE_MULTI_QUERY: bool = False
    CONVERSATION_ENABLE_CACHING: bool = True
    CONVERSATION_ENABLE_STREAMING: bool = True
    CONVERSATION_ENABLE_CLARIFICATION: bool = True
    CONVERSATION_ENABLE_NEIGHBOR_EXPANSION: bool = True
    CONVERSATION_ENABLE_RERANKER: bool = True
    CONVERSATION_ENABLE_SUMMARIES: bool = True
    CONVERSATION_ENABLE_MEMORY: bool = True
    
    CONVERSATION_DEFAULT_MODE: str = "General Chat"
    CONVERSATION_CACHE_PROVIDER: str = "memory"
    CONVERSATION_MEMORY_PROVIDER: str = "tiered"
    
    CONVERSATION_CLARIFICATION_THRESHOLD: float = 0.8
    CONVERSATION_SUMMARY_TOKEN_THRESHOLD: int = 4000
    CONVERSATION_MAX_CONTEXT_TURNS: int = 20
    CONVERSATION_WORKING_MEMORY_SIZE: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )

    # Namespaces
    @property
    def app(self) -> AppSettings:
        """Grouped App settings."""
        return AppSettings(
            name=self.APP_NAME,
            version=self.VERSION,
            environment=self.ENVIRONMENT,
            debug=self.DEBUG,
        )

    @property
    def database(self) -> DatabaseSettings:
        """Grouped database settings."""
        return DatabaseSettings(url=self.DATABASE_URL)

    @property
    def upload(self) -> UploadSettings:
        """Grouped upload settings."""
        return UploadSettings(
            directory=self.UPLOAD_DIR,
            max_file_size_mb=self.MAX_FILE_SIZE_MB,
        )

    @property
    def embedding(self) -> EmbeddingSettings:
        """Grouped embedding settings."""
        return EmbeddingSettings(
            model=self.EMBEDDING_MODEL,
            dimension=self.EMBEDDING_DIMENSION,
        )

    @property
    def worker(self) -> WorkerSettings:
        """Grouped worker settings."""
        return WorkerSettings(concurrency=self.WORKER_CONCURRENCY)

    @property
    def vector_search(self) -> VectorSearchSettings:
        """Grouped vector search settings."""
        return VectorSearchSettings(
            default_limit=self.RAG_TOP_K,
            similarity_threshold=self.RAG_REJECT_THRESHOLD,
            reject_threshold=self.RAG_REJECT_THRESHOLD,
            weak_threshold=self.RAG_WEAK_THRESHOLD,
            strong_threshold=self.RAG_STRONG_THRESHOLD,
        )
        
    @property
    def retrieval(self) -> RetrievalSettings:
        """Grouped enterprise retrieval engine settings."""
        return RetrievalSettings(
            metadata_filter_enabled=self.RETRIEVAL_METADATA_FILTER_ENABLED,
            bm25_enabled=self.RETRIEVAL_BM25_ENABLED,
            hybrid_enabled=self.RETRIEVAL_HYBRID_ENABLED,
            context_compression_enabled=self.RETRIEVAL_CONTEXT_COMPRESSION_ENABLED,
            top_k_dense=self.RETRIEVAL_TOP_K_DENSE,
            top_k_sparse=self.RETRIEVAL_TOP_K_SPARSE,
            top_k_hybrid=self.RETRIEVAL_TOP_K_HYBRID,
            top_k_rerank=self.RETRIEVAL_TOP_K_RERANK,
            dense_weight=self.RETRIEVAL_DENSE_WEIGHT,
            sparse_weight=self.RETRIEVAL_SPARSE_WEIGHT,
            rrf_constant=self.RETRIEVAL_RRF_CONSTANT,
            minimum_similarity=self.RETRIEVAL_MINIMUM_SIMILARITY,
            weak_threshold=self.RETRIEVAL_WEAK_THRESHOLD,
            strong_threshold=self.RETRIEVAL_STRONG_THRESHOLD,
            query_rewrite_threshold=self.RETRIEVAL_QUERY_REWRITE_THRESHOLD,
            followup_detection_threshold=self.RETRIEVAL_FOLLOWUP_DETECTION_THRESHOLD,
            reranker_provider=self.RETRIEVAL_RERANKER_PROVIDER,
            reranker_model=self.RETRIEVAL_RERANKER_MODEL,
            entity_provider=self.RETRIEVAL_ENTITY_PROVIDER,
            keyword_provider=self.RETRIEVAL_KEYWORD_PROVIDER,
            rewrite_provider=self.RETRIEVAL_REWRITE_PROVIDER,
            reranker_batch_size=self.RETRIEVAL_RERANKER_BATCH_SIZE,
            reranker_timeout=self.RETRIEVAL_RERANKER_TIMEOUT,
            retrieval_timeout=self.RETRIEVAL_TIMEOUT,
            maximum_context_tokens=self.RETRIEVAL_MAXIMUM_CONTEXT_TOKENS,
            maximum_candidate_chunks=self.RETRIEVAL_MAXIMUM_CANDIDATE_CHUNKS,
            minimum_chunk_size=self.RETRIEVAL_MINIMUM_CHUNK_SIZE,
            maximum_chunk_size=self.RETRIEVAL_MAXIMUM_CHUNK_SIZE,
            retry_counts=self.RETRIEVAL_RETRY_COUNTS,
            neighbor_expansion_enabled=self.RETRIEVAL_NEIGHBOR_EXPANSION_ENABLED,
            maximum_neighbor_depth=self.RETRIEVAL_MAXIMUM_NEIGHBOR_DEPTH,
            chunk_expansion_count=self.RETRIEVAL_CHUNK_EXPANSION_COUNT
        )

    @property
    def generation(self) -> GenerationSettings:
        """Grouped enterprise generation engine settings."""
        return GenerationSettings(
            enforce_extractive_drafting=self.GENERATION_ENFORCE_EXTRACTIVE_DRAFTING,
            hallucination_tolerance=self.GENERATION_HALLUCINATION_TOLERANCE,
            llm_enhancer_provider=self.GENERATION_LLM_ENHANCER_PROVIDER,
            formatter_provider=self.GENERATION_FORMATTER_PROVIDER,
            streaming_provider=self.GENERATION_STREAMING_PROVIDER,
            citation_provider=self.GENERATION_CITATION_PROVIDER,
            compression_provider=self.GENERATION_COMPRESSION_PROVIDER,
            prompt_builder_provider=self.GENERATION_PROMPT_BUILDER_PROVIDER,
            quality_engine_provider=self.GENERATION_QUALITY_ENGINE_PROVIDER,
            max_input_tokens=self.GENERATION_MAX_INPUT_TOKENS,
            max_output_tokens=self.GENERATION_MAX_OUTPUT_TOKENS,
            enhancer_timeout=self.GENERATION_ENHANCER_TIMEOUT,
            enhancer_retry_counts=self.GENERATION_ENHANCER_RETRY_COUNTS,
            response_cache_enabled=self.GENERATION_RESPONSE_CACHE_ENABLED,
            response_cache_ttl=self.GENERATION_RESPONSE_CACHE_TTL
        )

    @property
    def conversation(self) -> ConversationSettings:
        """Grouped enterprise conversation intelligence settings."""
        return ConversationSettings(
            enable_multi_query=self.CONVERSATION_ENABLE_MULTI_QUERY,
            enable_caching=self.CONVERSATION_ENABLE_CACHING,
            enable_streaming=self.CONVERSATION_ENABLE_STREAMING,
            enable_clarification=self.CONVERSATION_ENABLE_CLARIFICATION,
            enable_neighbor_expansion=self.CONVERSATION_ENABLE_NEIGHBOR_EXPANSION,
            enable_reranker=self.CONVERSATION_ENABLE_RERANKER,
            enable_summaries=self.CONVERSATION_ENABLE_SUMMARIES,
            enable_memory=self.CONVERSATION_ENABLE_MEMORY,
            default_conversation_mode=self.CONVERSATION_DEFAULT_MODE,
            cache_provider=self.CONVERSATION_CACHE_PROVIDER,
            memory_provider=self.CONVERSATION_MEMORY_PROVIDER,
            clarification_ambiguity_threshold=self.CONVERSATION_CLARIFICATION_THRESHOLD,
            summary_token_threshold=self.CONVERSATION_SUMMARY_TOKEN_THRESHOLD,
            max_context_turns=self.CONVERSATION_MAX_CONTEXT_TURNS,
            working_memory_size=self.CONVERSATION_WORKING_MEMORY_SIZE
        )

    @property
    def logging(self) -> LoggingSettings:
        """Grouped logging settings."""
        return LoggingSettings(
            level=self.LOG_LEVEL,
            format_str=self.LOG_FORMAT,
        )

    @property
    def api(self) -> ApiSettings:
        """Grouped API settings."""
        return ApiSettings(host=self.HOST, port=self.PORT)

    @property
    def llm(self) -> LlmSettings:
        """Grouped LLM settings."""
        return LlmSettings(
            provider=self.LLM_PROVIDER,
            model=self.LLM_MODEL,
            api_key=self.GEMINI_API_KEY,
        )


settings = Settings()
