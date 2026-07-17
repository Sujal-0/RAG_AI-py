import asyncio
import os
import sys

from app.database.session import async_session
from app.repositories.document_repository import DocumentRepository
from app.database.models import DocumentChunk
from sqlalchemy import select

async def main():
    async with async_session() as session:
        docs = await DocumentRepository.get_documents_list(session)
        print("Documents in DB:")
        for d in docs:
            print(f"File: {d['filename']}, Status: {d['status']}, Chunks: {d['chunk_count']}")

        # Let's also search for 'ananya gupta' in the chunks
        print("\nSearching for 'ananya' in chunks:")
        stmt = select(DocumentChunk.text, DocumentChunk.heading).filter(DocumentChunk.text.ilike("%ananya%"))
        res = await session.execute(stmt)
        for text, heading in res:
            print(f"Heading: {heading}")
            print(f"Text: {text[:100]}...")

if __name__ == '__main__':
    asyncio.run(main())
