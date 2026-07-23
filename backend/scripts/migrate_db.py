import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

from app.core.settings import settings

logger = logging.getLogger("app")

async def main():
    db_url = settings.database.url
    if db_url.startswith("postgresql://"):
        base_url = db_url.split("?")[0]
        db_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "ssl" in settings.database.url.lower():
            db_url += "?ssl=require"

    print(f"Connecting to {db_url}")
    engine = create_async_engine(db_url, echo=True)
    
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE document_chunks ALTER COLUMN heading TYPE TEXT, ALTER COLUMN section TYPE TEXT;"))
            print("Successfully changed heading and section to TEXT.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
