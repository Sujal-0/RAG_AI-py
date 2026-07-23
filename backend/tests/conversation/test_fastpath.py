import pytest
from app.conversation.planner.decision_engine import DecisionEngine
from app.conversation.planner.query_normalizer import QueryNormalizer

class TestFastPath:
    def test_query_normalizer_unicode_emoji(self):
        assert QueryNormalizer.normalize("hello \U0001f60a") == "hello"
        assert QueryNormalizer.normalize("hi \U0001f680") == "hi"
        assert QueryNormalizer.normalize("what is AI") == "what is ai"

    def test_query_normalizer_whitespace_punctuation(self):
        assert QueryNormalizer.normalize("  hello   ") == "hello"
        assert QueryNormalizer.normalize("hi!!!") == "hi"
        assert QueryNormalizer.normalize("hello???") == "hello"
        assert QueryNormalizer.normalize("what is AI?!") == "what is ai"
        assert QueryNormalizer.normalize("good\t\tmorning\n") == "good morning"
        
    def test_query_normalizer_repeated_chars(self):
        assert QueryNormalizer.normalize("hii") == "hi"
        assert QueryNormalizer.normalize("hiii") == "hi"
        assert QueryNormalizer.normalize("heya") == "hey"
        assert QueryNormalizer.normalize("hellooo") == "hello"
        assert QueryNormalizer.normalize("byeee") == "bye"
        assert QueryNormalizer.normalize("thankssss") == "thanks"
        assert QueryNormalizer.normalize("asdfgh") == "asdfgh" # Gibberish shouldn't be collapsed unless same char

    @pytest.mark.parametrize("query, expected_intent, expected_processed", [
        # Empty
        ("", "Empty", ""),
        ("   ", "Empty", ""),
        ("???", "Empty", ""),
        ("\U0001f60a", "Empty", ""),
        
        # Greetings
        ("hi", "Greeting", "hi"),
        ("hii", "Greeting", "hi"),
        ("hello", "Greeting", "hello"),
        ("heya", "Greeting", "hey"),
        ("hey", "Greeting", "hey"),
        ("yo", "Greeting", "yo"),
        ("sup", "Greeting", "sup"),
        ("good morning", "Greeting", "good morning"),
        ("namaste", "Greeting", "namaste"),
        ("hola", "Greeting", "hola"),
        ("hi bro", "Greeting", "hi bro"),
        ("hello ji", "Greeting", "hello ji"),
        ("hello bot", "Greeting", "hello bot"),
        ("hello AI", "Greeting", "hello ai"),
        ("hello there", "Greeting", "hello there"),
        
        # Greeting + Question
        ("hello what is AI", "Definition", "what is ai"),
        ("hi summarize company", "Summary", "summarize company"),
        ("hey compare AI and Blockchain", "Comparison", "compare ai and blockchain"),
        
        # Greeting + Gibberish
        ("hi asdfgh", "Gibberish", "asdfgh"),
        ("hello 123123123", "Gibberish", "123123123"),
        
        # Thanks
        ("thanks", "Thanks", "thanks"),
        ("thank you", "Thanks", "thank you"),
        ("tysm", "Thanks", "tysm"),
        ("appreciate it", "Thanks", "appreciate it"),
        
        # Goodbye
        ("bye", "Goodbye", "bye"),
        ("goodbye", "Goodbye", "goodbye"),
        ("see ya", "Goodbye", "see ya"),
        ("take care", "Goodbye", "take care"),
        
        # Identity
        ("who are you", "AssistantIdentity", "who are you"),
        ("what is your name", "AssistantIdentity", "what is your name"),
        ("who built you", "AssistantIdentity", "who built you"),
        ("are you chatgpt", "AssistantIdentity", "are you chatgpt"),
        
        # Gibberish
        ("asdfgh", "Gibberish", "asdfgh"),
        ("qwertyuiop", "Gibberish", "qwertyuiop"),
        ("zxcvbnm", "Gibberish", "zxcvbnm"),
        ("123123123", "Gibberish", "123123123"),
        ("kjashdkjashd", "Gibberish", "kjashdkjashd"),
        ("dsas", "Gibberish", "dsas"),
        ("jajs", "Gibberish", "jajs"),
        ("sasa", "Gibberish", "sasa"),
        ("nfekw", "Gibberish", "nfekw"),
        ("uyrt47yue", "Gibberish", "uyrt47yue"),
        ("nfew", "Gibberish", "nfew"),
        
        # Knowledge Queries
        ("What is Mobiloitte", "Definition", "what is mobiloitte"),
        ("Explain AI", "Explanation", "explain ai"),
        ("Compare AI and Blockchain", "Comparison", "compare ai and blockchain"),
        ("What are the advantages of Python", "Advantages", "what are the advantages of python"),
        
        # Mixed Cases
        ("Hi!!!!", "Greeting", "hi"),
        ("Hello \U0001f60a", "Greeting", "hello"),
        ("HELLO", "Greeting", "hello"),
        ("good     morning", "Greeting", "good morning"),
        ("hi who are you", "AssistantIdentity", "who are you"),
        ("hello thanks", "Thanks", "thanks"),
        ("hey bye", "Goodbye", "bye"),
    ])
    def test_decision_engine(self, query, expected_intent, expected_processed):
        res = DecisionEngine.classify(query)
        assert res["intent"] == expected_intent
        assert res["processed_query"] == expected_processed
