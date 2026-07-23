import pytest
from app.conversation.planner.decision_engine import DecisionEngine
from app.conversation.planner.query_normalizer import QueryNormalizer

class TestFastPathBulk:
    def test_greetings_bulk(self):
        # Generate 50 greetings
        greetings = ["hi", "hello", "hey", "hiya", "yo", "sup", "good morning", "good evening"]
        for g in greetings:
            for i in range(5):
                # test with varying spaces
                q = (" " * i) + g + (" " * i)
                res = DecisionEngine.classify(q)
                assert res["intent"] == "Greeting", f"Failed on {q}"
                
    def test_gibberish_bulk(self):
        # Generate 100 gibberish queries
        gibberish = ["asdfgh", "kjashdkjashd", "qwertyuiop", "zxcvbnm", "qqqqqq", "123123123"]
        for g in gibberish:
            for i in range(15):
                q = g * (i + 1)
                res = DecisionEngine.classify(q)
                assert res["intent"] == "Gibberish", f"Failed on {q}"

    def test_knowledge_bulk(self):
        # Generate 100 knowledge queries
        bases = ["what is AI", "explain blockchain", "how does python work", "cost of mobiloitte"]
        for b in bases:
            for i in range(25):
                q = b + ("?" * (i % 3))
                res = DecisionEngine.classify(q)
                assert res["intent"] in ["Definition", "Explanation", "KnowledgeQuery"], f"Failed on {q}"
                
    def test_empty_bulk(self):
        # Generate 50 empty queries
        for i in range(50):
            q = " " * i
            res = DecisionEngine.classify(q)
            assert res["intent"] == "Empty", f"Failed on '{q}'"

