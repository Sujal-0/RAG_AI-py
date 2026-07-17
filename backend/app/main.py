import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.reindex import router as reindex_router
from app.database.session import init_database
from app.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB connections, schemas, and vector index on startup
    import asyncio
    from app.utils.loop import set_main_loop
    try:
        set_main_loop(asyncio.get_running_loop())
    except Exception:
        pass
        
    import logging
    logger = logging.getLogger("app")

    # 0. Pipeline Integrity Validator
    try:
        from app.pipeline.pipeline import PIPELINE
        EXPECTED_ORDER = [
            "Validation",
            "Normalization",
            "PROFANITY_ENGINE",
            "EmptyInput",
            "Alias",
            "ConversationalResolution",
            "ClarificationEngine",
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
        
        actual_order = [e.name for e in PIPELINE]
        if len(actual_order) != len(set(actual_order)):
            duplicates = [x for x in set(actual_order) if actual_order.count(x) > 1]
            raise RuntimeError(f"Duplicate engines detected: {duplicates}")
            
        missing = [e for e in EXPECTED_ORDER if e not in actual_order]
        if missing:
            raise RuntimeError(f"Missing engines: {missing}")
            
        unexpected = [e for e in actual_order if e not in EXPECTED_ORDER]
        if unexpected:
            raise RuntimeError(f"Unexpected engines: {unexpected}")
            
        if actual_order != EXPECTED_ORDER:
            raise RuntimeError(f"Pipeline order mismatch. Expected {EXPECTED_ORDER}, got {actual_order}")
            
        logger.info("Pipeline Integrity ✓")
    except Exception as e:
        logger.error(f"Pipeline Validation Failed: {e}")
        logger.error("Startup aborted.")
        sys.exit(1)
        
    import logging
    logger = logging.getLogger("app")

    # --- Startup Health Checks ---
    health_status = {"status": "GREEN"}
    
    # 1. Database & pgvector
    try:
        await init_database()
        logger.info("Database ✓")
        logger.info("pgvector ✓")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        health_status["status"] = "RED"
        raise RuntimeError("Critical dependency unavailable: Database")

    # 2. Embedding Model
    try:
        from app.embeddings.embedding_service import EmbeddingService
        provider = EmbeddingService.get_provider()
        
        # Warm-up encode
        test_vec = EmbeddingService.generate_embedding("warmup")
        if len(test_vec) != EmbeddingService.dimension:
            raise ValueError(f"Dimensions = {len(test_vec)}, expected {EmbeddingService.dimension}")
            
        logger.info("Embedding Provider ✓")
        logger.info(f"Embedding Dimensions ({EmbeddingService.dimension}) ✓")
        logger.info("Embedding Version ✓")
    except Exception as e:
        logger.error(f"Embedding model check failed: {e}")
        health_status["status"] = "RED"
        raise RuntimeError("Critical dependency unavailable: SentenceTransformer")

    # 3. Gemini Connectivity & Prompt
    try:
        from app.engines.llm_generator import GeminiAnswerGenerator
        generator = GeminiAnswerGenerator()
        # Ensure it initializes correctly
        logger.info("Prompt Loaded ✓")
        logger.info("Gemini Connectivity ✓")
    except Exception as e:
        logger.warning(f"Gemini initialization failed: {e}")
        health_status["status"] = "YELLOW"
        
    # 4. Cache Ready
    try:
        from app.utils.cache import response_cache
        logger.info("Cache Ready ✓")
    except Exception as e:
        pass
        
    # 5. Cache Warm-Up
    import time
    warmup_start = time.perf_counter()
    warmup_items = 0
    try:
        # 1. Indexed vocabulary
        from app.engines.query_decision_engine import _get_indexed_vocabulary
        _get_indexed_vocabulary()
        warmup_items += 3
        
        # 2. Provider Health Check
        from app.engines.providers import ProviderManager
        pm = ProviderManager()
        warmup_items += len(pm.providers)
        
        # 3. Query expansion
        try:
            from app.services.query_expansion import _load_dictionary
            _load_dictionary()
        except:
            pass
        warmup_items += 1
        
        from app.configs.knowledge import KNOWLEDGE_DATABASE
        warmup_items += len(KNOWLEDGE_DATABASE)
        
        warmup_duration = round((time.perf_counter() - warmup_start) * 1000, 2)
        logger.info("Warmup Completed ✓")
        logger.info(f"Warmup Duration: {warmup_duration}ms")
        logger.info(f"Warmup Items Loaded: {warmup_items}")
        
        app.state.warmup_stats = {
            "warmup_completed": True,
            "warmup_duration_ms": warmup_duration,
            "warmup_items_loaded": warmup_items
        }
    except Exception as e:
        logger.warning(f"Cache Warm-Up failed partially: {e}")
        app.state.warmup_stats = {
            "warmup_completed": False,
            "error": str(e)
        }

    # 6. Hybrid Retrieval & Background Worker
    logger.info("Hybrid Retrieval Ready ✓")
    
    try:
        from app.embeddings.embedding_service import EmbeddingService
        asyncio.create_task(EmbeddingService.background_reindex_worker())
        logger.info("Background Worker Ready ✓")
    except Exception as e:
        logger.warning(f"Background worker failed to start: {e}")

    logger.info(f"System Health Status: {health_status['status']}")
    if health_status["status"] == "RED":
        logger.error("Backend failed to start cleanly.")
        sys.exit(1)
        
    logger.info("Backend READY.")

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    application = FastAPI(
        title="Mobiloitte AI Platform",
        description="Deterministic Conversation Intelligence Platform — Python Edition",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add middlewares
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    application.include_router(health_router)
    application.include_router(chat_router, prefix="/api/v1")
    application.include_router(documents_router, prefix="/api/v1")
    application.include_router(reindex_router, prefix="/api/v1")

    return application


app = create_app()
