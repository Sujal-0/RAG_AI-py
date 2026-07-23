import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.session import init_database
from app.generation.orchestrator.generation_orchestrator import GenerationOrchestrator
from app.retrievers.retrieval_orchestrator import RetrievalResult
from app.engines.query.query_analyzer import NormalizedQuery
from app.engines.query.strategy_engine import RetrievalStrategy

class MockChunk:
    def __init__(self):
        self.id = "test_1"
        self.text = "Machine learning is a subset of artificial intelligence."
        self.chunk_metadata = {"document_id": "doc_1"}
        self.chunk_index = 0
        self.token_count = 10

async def test_generation():
    print("Initializing database...")
    await init_database()
    
    print("Initializing GenerationOrchestrator...")
    
    strategy = RetrievalStrategy(
        strategy_name="hybrid",
        dense_weight=0.5,
        sparse_weight=0.5,
        require_exact_metadata=False,
        target_chunk_types=[],
        expand_neighbors=False,
        top_k=5
    )
    
    retrieval_result = RetrievalResult(
        trace_id="test-trace",
        original_query="What is machine learning?",
        normalized_query=NormalizedQuery(
            original_text="What is machine learning?",
            normalized_text="what is machine learning",
            language="en",
            question_type="what",
            response_expectation="summary"
        ),
        rewritten_query="What is machine learning?",
        intent="Information Seeking",
        strategy=strategy,
        evidence=[
            {
                "chunk": MockChunk(),
                "hybrid_score": 0.9
            }
        ],
        confidence="HIGH",
        confidence_score=0.9,
        metrics={},
        debug_info={}
    )
    
    print("Calling generate...")
    response = await GenerationOrchestrator.generate(retrieval_result)
    
    print("\n--- Generated Response ---")
    print(response.content.encode("utf-8", "ignore").decode("utf-8", "ignore"))
    print("\n--- Citations ---")
    print(response.citations)
    
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_generation())
