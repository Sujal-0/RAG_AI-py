"""Behavioral and integration tests for Phase 5 core layer.

Generates 1500+ assertions verifying alias mapping, Query Understanding,
Knowledge retrieval, Fallback routing, confidence boundaries, and regressions.
"""

from typing import Any
from app.pipeline.process import process_query
from app.pipeline.intents import Intent
from app.configs.aliases import ALIASES
from app.configs.knowledge import KNOWLEDGE_DATABASE


def execute_test_query(
    query: str,
    expected_intent: str | Intent,
    expected_confidence: float = None,
    expect_success: bool = True,
) -> dict[str, Any]:
    """Helper to process a query and verify standard output properties."""
    res = process_query(
        query,
        "sess-phase5-test",
        "req-phase5-test",
        metadata={"deterministicResponse": True},
    )
    assert res["success"] is expect_success, f"Failed success check on query: {query}"
    assert (
        res["intent"] == expected_intent
    ), f"Failed intent check on query: {query}. Got: {res['intent']}, expected: {expected_intent}"

    if expected_confidence is not None:
        assert abs(res["confidence"] - expected_confidence) < 1e-5, (
            f"Failed confidence boundary on query: {query}. "
            f"Got: {res['confidence']}, expected: {expected_confidence}"
        )

    return res


# ----------------------------------------------------------------------
# 1. ALIAS RESOLUTION TESTS
# ----------------------------------------------------------------------
def test_alias_resolution_rules() -> None:
    """Verify alias mapping rules expand to correct canonical forms."""
    # Test every defined alias in lowercase, uppercase, and with padding
    for alias_phrase, canonical in ALIASES.items():
        q_simple = f"tell me about {alias_phrase}"
        res_simple = process_query(
            q_simple,
            "sess-alias",
            "req-alias",
            metadata={"deterministicResponse": True},
        )
        assert res_simple["success"] is True
        # Resolved query must contain the canonical term
        assert (
            canonical in res_simple["resolvedQuery"].lower()
        ), f"Alias '{alias_phrase}' did not resolve to '{canonical}' in: {res_simple['resolvedQuery']}"

        # Upper case check
        q_upper = f"Tell me about {alias_phrase.upper()}"
        res_upper = process_query(
            q_upper,
            "sess-alias",
            "req-alias",
            metadata={"deterministicResponse": True},
        )
        assert canonical in res_upper["resolvedQuery"].lower()

        # Whitespace padding check
        q_pad = f"tell me about    {alias_phrase}   now"
        res_pad = process_query(
            q_pad,
            "sess-alias",
            "req-alias",
            metadata={"deterministicResponse": True},
        )
        assert canonical in res_pad["resolvedQuery"].lower()


# ----------------------------------------------------------------------
# 2. CENTRAL KNOWLEDGE EXACT & PHRASE MATCHES
# ----------------------------------------------------------------------
def test_knowledge_exact_and_phrase_matches() -> None:
    """Verify that every knowledge entry is matchable through triggers and titles."""
    for entry in KNOWLEDGE_DATABASE:
        # Test Exact Match on Title (Confidence = 1.00)
        res_title = execute_test_query(entry.title, entry.intent_id, 1.00)
        assert entry.answer in res_title["answer"]

        # Test Exact Match on Intent ID (Confidence = 1.00)
        res_id = execute_test_query(entry.intent_id, entry.intent_id, 1.00)
        assert entry.answer in res_id["answer"]

        # Test trigger phrases (Exact / Phrase match: Confidence = 1.00 or 0.99)
        for phrase in entry.trigger_phrases:
            res_phrase = execute_test_query(phrase, entry.intent_id)
            assert res_phrase["confidence"] >= 0.99
            assert entry.answer in res_phrase["answer"]


# ----------------------------------------------------------------------
# 3. DETAILED CONFIDENCE MODELS (Keyword Overlap & Partial matches)
# ----------------------------------------------------------------------
def test_layered_confidence_matching() -> None:
    """Verify keyword overlap confidence levels: 0.95 (2+ kws), 0.82 (1 kw), 0.63 (partial)."""
    # 0.95 Confidence: 2+ keyword overlap
    test_cases_95 = [
        ("mobiloitte overview details", "COMPANY_OVERVIEW"),
        ("ai machine learning capabilities", "AI_SERVICES"),
        ("aws devops cloud integration", "CLOUD_SERVICES"),
        ("solidity smart contracts blockchain", "BLOCKCHAIN"),
        ("flutter mobile app systems", "MOBILE_DEVELOPMENT"),
    ]
    for q, intent in test_cases_95:
        execute_test_query(q, intent, 0.95)

    # 0.82 Confidence: 1 keyword overlap
    test_cases_82 = [
        ("mobiloitte details", "COMPANY_OVERVIEW"),
        ("tell me about solidity", "BLOCKCHAIN"),
        ("custom flutter apps", "MOBILE_DEVELOPMENT"),
        ("what stack is used", "TECHNOLOGIES"),
    ]
    for q, intent in test_cases_82:
        execute_test_query(q, intent, 0.82)

    # 0.63 Confidence: Partial word matches (which fall back under 0.70 threshold)
    test_cases_63 = [
        ("tell me about solid", Intent.FALLBACK),  # 'solid' in solidity
        ("custom flutt apps", Intent.FALLBACK),  # 'flutt' in flutter
        ("mobiloit corporate details", Intent.FALLBACK),  # 'mobiloit' in mobiloitte
    ]
    for q, intent in test_cases_63:
        execute_test_query(q, intent, 0.63)


# ----------------------------------------------------------------------
# 4. MIXED GREETINGS / GOODBYES / THANKS / SMALL TALK COMBINATIONS
# ----------------------------------------------------------------------
def test_mixed_conversational_flows() -> None:
    """Verify conversational prefixes combine cleanly with knowledge base queries."""
    greetings = ["hello", "hi", "hey", "good morning", "hola"]
    thanks_phrases = ["thanks", "thank you", "thx"]
    goodbyes = ["bye", "goodbye", "later", "see you"]
    small_talk_phrases = ["how are you", "who are you", "what can you do"]

    # Target business queries to combine with prefixes
    business_targets = [
        ("where is office", "OFFICE_LOCATIONS"),
        ("what services do you offer", "SERVICES"),
        ("careers openings", "CAREERS"),
        ("do you hire interns", "INTERNSHIP"),
        ("tell me about cloud solutions", "CLOUD_SERVICES"),
    ]

    # Greeting + Business -> Intent: COMPANY_INTENT, Prefix prepended
    for greet in greetings:
        for b_query, target_intent in business_targets:
            q = f"{greet} {b_query}"
            res = execute_test_query(q, "COMPANY_INTENT")
            ans_lower = res["answer"].lower()
            assert any(
                g in ans_lower
                for g in [
                    "hello",
                    "hi",
                    "hey",
                    "morning",
                    "afternoon",
                    "evening",
                    "namaste",
                    "welcome",
                    "pranam",
                    "adaab",
                    "satsriakal",
                    "vanakkam",
                    "hola",
                    "bonjour",
                    "ciao",
                    "hallo",
                    "konnichiwa",
                    "yo",
                ]
            )

    # Thanks + Business -> Intent: COMPANY_INTENT, Prefix prepended
    for thx in thanks_phrases:
        for b_query, target_intent in business_targets:
            q = f"{thx} {b_query}"
            res = execute_test_query(q, "COMPANY_INTENT")
            assert (
                "welcome" in res["answer"].lower()
                or "pleasure" in res["answer"].lower()
                or "help" in res["answer"].lower()
            )

    # Goodbye + Business -> Intent: COMPANY_INTENT, Prefix prepended
    for bye in goodbyes:
        for b_query, target_intent in business_targets:
            q = f"{bye} {b_query}"
            res = execute_test_query(q, "COMPANY_INTENT")
            assert (
                "bye" in res["answer"].lower()
                or "see you" in res["answer"].lower()
                or "care" in res["answer"].lower()
            )

    # Small Talk + Business -> Intent: COMPANY_INTENT, Prefix prepended
    for st in small_talk_phrases:
        for b_query, target_intent in business_targets:
            q = f"{st} {b_query}"
            res = execute_test_query(q, "COMPANY_INTENT")
            assert len(res["answer"].split(" ")) > 3


# ----------------------------------------------------------------------
# 5. REGRESSIONS, FALSE POSITIVES, AND FALLBACK BOUNDARIES
# ----------------------------------------------------------------------
def test_fallback_and_boundary_safety() -> None:
    """Ensure non-matching, gibberish, and low-confidence inputs drop into appropriate engines."""
    # Keyboard smashes (Gibberish)
    keyboard_smashes = [
        "xyzabc123",
        "asdfgqwe",
        "qwertyuiop",
        "hsjgwf",
        "hsdjwfsrh",
        "dhiashd",
        "m",
        "n",
        "d",
        "sh",
        "sg",
        "dj",
        "dhwi",
        "dwqug",
        "adhwi",
        "hieohc",
        "uguas",
        "hsdaj",
        "dhsahl",
        "alhalh",
        "nalkn",
        "asdfgh",
        "qwerty",
        "llllllll",
        "aaaaaaa",
        "pppppp",
        "sjkdhskjd",
        "qwertyui",
        "poiuytre",
        "lkjhgfd",
    ]
    for q in keyboard_smashes:
        res = execute_test_query(q, Intent.GIBBERISH)
        assert "I'm not sure what you meant. Could you rephrase your question? I'm here to help with anything related to Mobiloitte." in res["answer"]
        assert res["confidence"] == 1.0

    # Understandable out-of-scope queries (Fallback)
    fallbacks = [
        "random search query about nothing",
        "What is Elon Musk's salary?",
        "What is Mars population?",
    ]
    for q in fallbacks:
        res = execute_test_query(q, Intent.FALLBACK)
        assert "I don't have information about that." in res["answer"]
        assert res["confidence"] == 0.0

    # Low-confidence boundary matching (below 0.70 threshold)
    low_confidence_queries = [
        "tell me about solid",
        "custom flutt apps",
    ]
    for q in low_confidence_queries:
        res = execute_test_query(q, Intent.FALLBACK)
        assert "I don't have information about that." in res["answer"]
        # The query understanding metadata records the raw confidence of the best match
        trace = res["trace"]
        qu_trace = next(t for t in trace if t["engine"] == "QueryUnderstanding")
        assert qu_trace["confidence"] == 0.63

    # High-confidence alias boundary match
    execute_test_query("is there a branch in space", "OFFICE_LOCATIONS", 0.82)

    # False positives on greetings/goodbyes/thanks
    negatives = [
        ("history", Intent.FALLBACK),
        ("high school", Intent.FALLBACK),
        ("good company", Intent.FALLBACK),
    ]
    for q, expected in negatives:
        execute_test_query(q, expected)

    # Positive greeting tests
    positive_greetings = [
        "h i",
        "h e l l o",
        "h e l o",
        "HELLOOOO",
        "good     morning",
        "g m",
        "hiiii",
        "heyyyy",
    ]
    for q in positive_greetings:
        execute_test_query(q, Intent.GREETING)

    # Negative greeting tests (must NOT be GREETING intent)
    negative_greetings = [
        "history",
        "high",
        "helmet",
        "hero",
        "help",
        "hell",
    ]
    for q in negative_greetings:
        res = process_query(q, "sess-test", "req-test")
        assert res["intent"] != Intent.GREETING

    # Random punctuation (must become GIBBERISH)
    punctuation_queries = [
        "????",
        "!!!!",
        "^^^^",
    ]
    for q in punctuation_queries:
        execute_test_query(q, Intent.GIBBERISH)

    # Name remembering session memory tests
    res_greet = process_query("hello raj", "sess-name-remembering", "req-1")
    assert res_greet["intent"] == Intent.GREETING
    
    res_name = process_query("what is my name", "sess-name-remembering", "req-2")
    assert res_name["intent"] == Intent.SMALL_TALK
    assert "Raj" in res_name["answer"]


def test_greeting_time_adaptation() -> None:
    """Verify greeting engine adapts correct/incorrect greetings based on custom mock times."""
    # Test case 1: "Good morning" at 8 AM (no adaptation)
    res1 = process_query(
        "good morning",
        "sess-time-adapt-1",
        "req-time-1",
        metadata={"currentTime": "2026-07-13T08:00:00"}
    )
    assert res1["intent"] == Intent.GREETING
    assert "Good morning" in res1["answer"]

    # Test case 2: "Good morning" at 2 PM (adapts to good afternoon)
    res2 = process_query(
        "good morning",
        "sess-time-adapt-2",
        "req-time-2",
        metadata={"currentTime": "2026-07-13T14:00:00"}
    )
    assert res2["intent"] == Intent.GREETING
    assert "Good afternoon" in res2["answer"]

    # Test case 3: "Good afternoon" at 9 PM (adapts to good evening)
    res3 = process_query(
        "good afternoon",
        "sess-time-adapt-3",
        "req-time-3",
        metadata={"currentTime": "2026-07-13T21:30:00"}
    )
    assert res3["intent"] == Intent.GREETING
    assert "Good evening" in res3["answer"]

    # Test case 4: "Good night" at 2 PM (never adapted)
    res4 = process_query(
        "good night",
        "sess-time-adapt-4",
        "req-time-4",
        metadata={"currentTime": "2026-07-13T14:00:00"}
    )
    assert res4["intent"] == Intent.GREETING
    assert "Good night" in res4["answer"]

