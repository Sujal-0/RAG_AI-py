import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.pipeline.process import process_query
from app.utils.session import SessionStore

async def run_tests():
    print("Running Phase 8 Integration Tests...")

    # Set up session
    session_id = "test_session_123"
    SessionStore.clear()
    
    # Test 1: Simple Knowledge Query
    print("\nTest 1: Simple Query")
    res1 = process_query("What is the company mission?", session_id, "req-1")
    print("Intent:", res1["intent"])
    print("Decision:", res1["metadata"].get("decision"))
    print("Has RAG Trace:", any(t.get("engine") == "RAGRetrieval" for t in res1["trace"]))
    
    # Test 2: Follow up with Context Resolution
    print("\nTest 2: Context Follow-up")
    res2 = process_query("And what about the vision?", session_id, "req-2")
    print("Original Query:", res2["metadata"]["rawQuery"])
    print("Resolved Query:", res2["resolvedQuery"])
    print("Intent:", res2["intent"])
    
    # Test 3: Multi-intent Split test
    print("\nTest 3: Multi-Intent Split")
    res3 = process_query("Tell me about services and projects", session_id, "req-3")
    print("Resolved Query:", res3["resolvedQuery"])
    print("Multi-Intent:", res3["metadata"].get("multi_intent"))

    print("\nPhase 8 Tests Complete!")

if __name__ == "__main__":
    asyncio.run(run_tests())
