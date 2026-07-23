import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.settings import settings

async def main():
    db_url = settings.database.url
    if db_url.startswith("postgresql://"):
        base_url = db_url.split("?")[0]
        db_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "ssl" in settings.database.url.lower():
            db_url += "?ssl=require"

    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res1 = await conn.execute(text("SELECT status, chunk_count FROM document_versions ORDER BY created_at DESC LIMIT 1;"))
        version = res1.fetchone()
        print(f"Latest DocumentVersion: {version}")

        res2 = await conn.execute(text("SELECT COUNT(*) FROM document_chunks;"))
        chunks = res2.scalar()
        print(f"Total Chunks: {chunks}")
        
        res3 = await conn.execute(text("SELECT status, progress, error_message FROM processing_jobs ORDER BY start_time DESC LIMIT 1;"))
        job = res3.fetchone()
        print(f"Latest ProcessingJob: {job}")

if __name__ == "__main__":
    asyncio.run(main())
