import asyncio
import os
import sys

from app.database.session import async_session
from app.engines.rag_engine import RAGEngine
from app.pipeline.context import ConversationContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

async def main():
    engine = RAGEngine()
    
    # Fake a ConversationContext
    context = ConversationContext(request_id="test", session_id="test", original_query="Who is the Director of AI & Data Science at Mobiloitte?", resolved_query="who is the director of ai & data science at mobiloitte")
    
    # We must explicitly call retrieve_hybrid to see what chunks are retrieved
    from app.services.query_expansion import expand_query
    from app.embeddings.embedding_service import EmbeddingService
    
    expanded_query = expand_query(context.resolved_query)
    query_embedding = EmbeddingService.generate_embedding(expanded_query)
    
    print(f"Expanded Query: {expanded_query}")
    print(f"Embedding length: {len(query_embedding)}")
    
    async with async_session() as session:
        from app.repositories.document_repository import DocumentRepository
        retrieved = await DocumentRepository.hybrid_search(session, expanded_query, query_embedding, limit=10)
        
        print(f"\nRetrieved {len(retrieved)} chunks:")
        for i, c in enumerate(retrieved):
            print(f"[{i}] {c.get('filename')} | Score: {c.get('score')} | Method: {c.get('retrieval_method')}")
            print(f"Text: {c.get('text')[:100]}...\n")

if __name__ == '__main__':
    asyncio.run(main())
