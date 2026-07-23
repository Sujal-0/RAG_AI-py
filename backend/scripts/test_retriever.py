import asyncio
from app.database.session import init_database, get_engine, async_session
from app.engines.query.query_analyzer import QueryAnalyzer
from app.engines.query.strategy_engine import RetrievalStrategyEngine
from app.retrievers.metadata_filter import MetadataFilterEngine
from app.retrievers.dense_retriever import DenseRetriever
from app.retrievers.hybrid_retriever import HybridRetriever

async def test_retrieval():
    await init_database()
    raw_query = "What are the components of the Mobiloitte AI Platform?"
    
    normalized = QueryAnalyzer.analyze(raw_query)
    strategy = RetrievalStrategyEngine.determine_strategy("Architecture", "text")
    filters = MetadataFilterEngine.generate_filters(strategy, normalized, {})
    
    print("Filters:", filters)
    
    from app.database.session import async_session
    print("About to start async_session context")
    async with async_session() as session:
        print("Inside session context. Calling DenseRetriever.retrieve...")
        dense_results = await DenseRetriever.retrieve(
            session=session,
            query=raw_query,
            strategy=strategy,
            metadata_filters=filters,
            top_k=5
        )
        print("Dense Results:", len(dense_results))
        for res in dense_results:
            print(" - Score:", res.get("dense_score"))
            
        hybrid_results = await HybridRetriever.retrieve(
            session=session,
            original_query=normalized,
            rewritten_query=raw_query,
            strategy=strategy,
            metadata_filters=filters,
            top_k=5
        )
        print("Hybrid Results:", len(hybrid_results))

if __name__ == "__main__":
    asyncio.run(test_retrieval())
