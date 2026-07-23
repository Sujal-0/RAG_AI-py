import asyncio
import sys

from sqlalchemy import text

# Configure path so we can import from app
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import get_engine

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def flush_database():
    print("Connecting to pgvector database...")
    engine = get_engine()
    
    try:
        async with engine.begin() as conn:
            print("Executing CASCADE TRUNCATE on vector tables...")
            
            # Use CASCADE to safely delete all referencing records in chunks, versions, and jobs
            await conn.execute(text("TRUNCATE TABLE documents CASCADE;"))
            
            print("Vector database successfully flushed. Ready for fresh document ingestion.")
    except Exception as e:
        print(f"Failed to flush vectors: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(flush_database())
