"""Database connection and session management.

Configures connection pooling and initialization scripts for PostgreSQL + pgvector.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import settings
from app.database.models import Base

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger("app")

# Ensure PostgreSQL connection uses asyncpg async driver
db_url = settings.database.url
if db_url.startswith("postgresql://"):
    base_url = db_url.split("?")[0]
    db_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "ssl" in settings.database.url.lower():
        db_url += "?ssl=require"

db_is_available = False

engine = None
async_session = None

def get_engine():
    global engine, async_session
    if engine is None:
        from sqlalchemy.pool import NullPool
        try:
            engine = create_async_engine(
                db_url,
                poolclass=NullPool,
                pool_pre_ping=True,
                echo=False,
            )
            async_session = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        except Exception as e:
            logger.error(f"Failed to create async database engine: {e}")
            raise
    return engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injector yielding a database session context."""
    get_engine()
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_database() -> None:
    """Initialize database tables, extensions, and vector indexes.

    Raises an error gracefully if the connection fails.
    """
    try:
        eng = get_engine()
        async with eng.begin() as conn:
            # 1. Enable pgvector and uuid extensions
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))

            # 2. Create tables
            await conn.run_sync(Base.metadata.create_all)

            # 3. Create IVFFLAT index on document_chunks table using cosine similarity
            # Use 384 dimensions for all-MiniLM-L6-v2. Lists = 100 is standard.
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS chunk_embeddings_ivfflat_idx "
                "ON document_chunks USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);"
            ))

            # 4. Perform ANALYZE optimization
            await conn.execute(text("ANALYZE document_chunks;"))

        global db_is_available
        db_is_available = True
        logger.info("Neon PostgreSQL + pgvector database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failure: {e}")
        raise RuntimeError(f"Database unavailable: {e}") from e
