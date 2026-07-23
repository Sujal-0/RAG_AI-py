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
        res1 = await conn.execute(text("SELECT id, text, chunk_metadata FROM document_chunks LIMIT 3;"))
        chunks = res1.fetchall()
        for idx, c in enumerate(chunks):
            print(f"Chunk {idx}: metadata={c.chunk_metadata}, text={c.text[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
