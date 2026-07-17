import asyncio
from app.database.session import async_session
from sqlalchemy import select, func, text
from app.database.models import DocumentChunk, DocumentVersion, Document

async def main():
    query_lower = "who is the director of ai & data science at mobiloitte"
    async with async_session() as session:
        stmt = (
            select(
                DocumentChunk.text,
                func.ts_rank(
                    func.to_tsvector("english", DocumentChunk.text),
                    func.plainto_tsquery("english", query_lower),
                ).label("rank"),
            )
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(DocumentVersion.status == "ready_for_search")
            .where(
                func.to_tsvector("english", DocumentChunk.text).op("@@")(func.plainto_tsquery("english", query_lower))
            )
            .order_by(text("rank DESC"))
            .limit(5)
        )
        res = await session.execute(stmt)
        rows = res.all()
        print(f"plainto_tsquery results: {len(rows)}")
        for r in rows:
            print(f"Rank: {r.rank} - {r.text[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
