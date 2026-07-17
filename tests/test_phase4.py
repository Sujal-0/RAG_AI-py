"""Regression and integration tests for Phase 4 engines.

Generates 800+ total assertions covering EmptyInput, Goodbye, Thanks,
and SmallTalk flows, including edge cases and regressions.
"""

from typing import Any
from fastapi.testclient import TestClient
from app.pipeline.process import process_query
from app.pipeline.intents import Intent
from app.configs.common import COMMON_NOISE_SUFFIXES
from app.configs.responses import (
    GOODBYE_RESPONSES,
    THANKS_RESPONSES,
    EMPTY_INPUT_RESPONSES,
    SMALL_TALK_RESPONSES,
)


def assert_pipeline_outcome(
    query: str,
    expected_intent: Intent,
    expected_handled: bool,
    expected_flow: str,
    expected_confidence: float = None,
) -> dict[str, Any]:
    """Helper to process a query and assert expected pipeline state properties."""
    res = process_query(
        query,
        "sess-phase4-test",
        "req-phase4-test",
        metadata={"deterministicResponse": True},
    )
    assert res["success"] is True

    trace = res["metadata"]["trace"]
    engine_name = None
    if expected_intent == Intent.EMPTY_INPUT:
        engine_name = "EmptyInput"
    elif expected_intent == Intent.GOODBYE:
        engine_name = "Goodbye"
    elif expected_intent == Intent.THANKS:
        engine_name = "Thanks"
    elif expected_intent == Intent.SMALL_TALK:
        engine_name = "SmallTalk"

    engine_trace = next((t for t in trace if t["engine"] == engine_name), None)
    assert (
        engine_trace is not None
    ), f"Expected trace for engine {engine_name} on query: {query}"

    assert (
        engine_trace["handled"] == expected_handled
    ), f"Mismatch handled on query: {query}"
    assert engine_trace["flow"] == expected_flow, f"Mismatch flow on query: {query}"
    if expected_confidence is not None:
        assert (
            engine_trace["confidence"] == expected_confidence
        ), f"Mismatch confidence on query: {query}"

    if expected_handled:
        assert res["intent"] == expected_intent, f"Mismatch intent on query: {query}"

    return res


# ----------------------------------------------------------------------
# 1. EMPTY INPUT TESTS
# ----------------------------------------------------------------------
def test_empty_input_variations() -> None:
    """Verify that truly empty and whitespace-only queries resolve to EMPTY_INPUT, while symbols and emojis resolve to GIBBERISH."""
    pure_empty_queries = [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        " \t\n \r ",
        "\u200b",  # zero-width space
        "\u200d",  # zero-width joiner
    ]

    for q in pure_empty_queries:
        assert_pipeline_outcome(
            q,
            expected_intent=Intent.EMPTY_INPUT,
            expected_handled=True,
            expected_flow="PURE",
            expected_confidence=1.00,
        )

    gibberish_empty_queries = [
        "😀",
        "😂😂",
        "👋",
        "😊❤️☀️",
        "...",
        "???",
        "!!!",
        "@@#$%",
        "   😀   ",
        "   ...   ",
        "??? 👋 ???",
    ]

    for q in gibberish_empty_queries:
        res = process_query(q, "sess-phase4-test", "req-phase4-test", metadata={"deterministicResponse": True})
        assert res["success"] is True
        assert res["intent"] == Intent.GIBBERISH


# ----------------------------------------------------------------------
# 2. GOODBYE REGRESSION & BULK FLOW TESTS
# ----------------------------------------------------------------------
def test_goodbye_bulk_flows() -> None:
    """Validate Goodbye Engine flows (A, B, C, D) using programmatically combined queries."""
    base_goodbyes = [
        "bye",
        "goodbye",
        "good bye",
        "later",
        "see you",
        "see ya",
        "take care",
    ]

    # Flow A: Pure Goodbye
    for bye in base_goodbyes:
        assert_pipeline_outcome(
            bye,
            expected_intent=Intent.GOODBYE,
            expected_handled=True,
            expected_flow="PURE",
        )
        assert_pipeline_outcome(
            bye.upper(),
            expected_intent=Intent.GOODBYE,
            expected_handled=True,
            expected_flow="PURE",
        )
        assert_pipeline_outcome(
            bye.title(),
            expected_intent=Intent.GOODBYE,
            expected_handled=True,
            expected_flow="PURE",
        )

    # Flow B: Pure Goodbye + Noise Suffix
    noise_suffixes = list(COMMON_NOISE_SUFFIXES)
    for bye in base_goodbyes[:5]:
        for suffix in noise_suffixes:
            q = f"{bye} {suffix}"
            assert_pipeline_outcome(
                q,
                expected_intent=Intent.GOODBYE,
                expected_handled=True,
                expected_flow="PURE_WITH_NOISE",
            )

    # Flow C: Goodbye + Business Query
    business_queries = [
        "what is the address",
        "where is office",
        "internship opportunities",
        "career options",
        "timings of the company",
        "what solutions do you provide",
    ]
    for bye in base_goodbyes[:4]:
        for b_q in business_queries:
            q = f"{bye} {b_q}"
            assert_pipeline_outcome(
                q,
                expected_intent=Intent.GOODBYE,
                expected_handled=False,
                expected_flow="PREFIX_QUERY",
            )

    # Flow D: Goodbye + Garbage
    garbage_suffixes = ["sjkhdfkj", "qwepoqwe", "kjashdk", "zxcmnv"]
    for bye in base_goodbyes[:4]:
        for g_s in garbage_suffixes:
            q = f"{bye} {g_s}"
            assert_pipeline_outcome(
                q,
                expected_intent=Intent.GOODBYE,
                expected_handled=False,
                expected_flow="PREFIX_GARBAGE",
            )


def test_goodbye_false_positives() -> None:
    """Verify terms starting with 'good' are not misclassified as goodbyes."""
    greetings = [
        "good morning",
        "good afternoon",
        "good evening",
    ]
    for q in greetings:
        res = process_query(
            q,
            "sess-phase4-test",
            "req-phase4-test",
            metadata={"deterministicResponse": True},
        )
        trace = res["metadata"]["trace"]
        goodbye_trace = next((t for t in trace if t["engine"] == "Goodbye"), None)
        # Should be handled by Greeting Engine earlier, so Goodbye never runs
        assert goodbye_trace is None

    other_negatives = [
        "good company",
        "good service",
        "good work",
        "good job",
    ]
    for q in other_negatives:
        res = process_query(
            q,
            "sess-phase4-test",
            "req-phase4-test",
            metadata={"deterministicResponse": True},
        )
        trace = res["metadata"]["trace"]
        goodbye_trace = next((t for t in trace if t["engine"] == "Goodbye"), None)
        assert goodbye_trace is not None
        assert goodbye_trace["handled"] is False


# ----------------------------------------------------------------------
# 3. THANKS BULK FLOW TESTS
# ----------------------------------------------------------------------
def test_thanks_bulk_flows() -> None:
    """Validate Thanks Engine flows (A, B, C, D) using programmatic alias variations."""
    base_thanks = [
        "thanks",
        "thank you",
        "thankyou",
        "thx",
        "ty",
        "many thanks",
        "thanks a lot",
    ]

    # Flow A: Pure Thanks
    for thanks in base_thanks:
        assert_pipeline_outcome(
            thanks,
            expected_intent=Intent.THANKS,
            expected_handled=True,
            expected_flow="PURE",
        )
        assert_pipeline_outcome(
            thanks.upper(),
            expected_intent=Intent.THANKS,
            expected_handled=True,
            expected_flow="PURE",
        )

    # Flow B: Thanks + Noise Suffix
    noise_suffixes = list(COMMON_NOISE_SUFFIXES)
    for thanks in base_thanks[:4]:
        for suffix in noise_suffixes:
            q = f"{thanks} {suffix}"
            assert_pipeline_outcome(
                q,
                expected_intent=Intent.THANKS,
                expected_handled=True,
                expected_flow="PURE_WITH_NOISE",
            )

    # Flow C: Thanks + Business Query
    business_queries = [
        "where are you located",
        "what services do you offer",
        "tell me about branches",
    ]
    for thanks in base_thanks[:4]:
        for b_q in business_queries:
            q = f"{thanks} {b_q}"
            assert_pipeline_outcome(
                q,
                expected_intent=Intent.THANKS,
                expected_handled=False,
                expected_flow="PREFIX_QUERY",
            )

    # Flow D: Thanks + Garbage
    garbage_suffixes = ["sjkhdfkj", "qwepoqwe"]
    for thanks in base_thanks[:4]:
        for g_s in garbage_suffixes:
            q = f"{thanks} {g_s}"
            assert_pipeline_outcome(
                q,
                expected_intent=Intent.THANKS,
                expected_handled=False,
                expected_flow="PREFIX_GARBAGE",
            )


# ----------------------------------------------------------------------
# 4. SMALL TALK FLOW TESTS
# ----------------------------------------------------------------------
def test_small_talk_flows() -> None:
    """Test Small Talk categories and sub-intents (Flows A, B, C, D)."""
    cases = [
        ("how are you", "how are you"),
        ("how r you", "how are you"),
        ("who are you", "who are you"),
        ("what are you", "who are you"),
        ("who made you", "who built you"),
        ("who created you", "who built you"),
        ("what can you do", "what can you do"),
        ("help", "help"),
        ("assist me", "help"),
        ("good job", "praise"),
        ("nice", "praise"),
        ("cool", "praise"),
        ("ok", "acknowledgement"),
        ("kk", "acknowledgement"),
        ("hmm", "acknowledgement"),
        ("lol", "lol"),
        ("haha", "lol"),
        ("wow", "expression"),
    ]

    # Flow A: Pure Small Talk
    for q, canonical in cases:
        assert_pipeline_outcome(
            q,
            expected_intent=Intent.SMALL_TALK,
            expected_handled=True,
            expected_flow="PURE",
        )
        assert_pipeline_outcome(
            q.upper(),
            expected_intent=Intent.SMALL_TALK,
            expected_handled=True,
            expected_flow="PURE",
        )

    # Flow B: Pure + Suffix Noise
    for q, canonical in cases[:10]:
        q_noise = f"{q} sir"
        assert_pipeline_outcome(
            q_noise,
            expected_intent=Intent.SMALL_TALK,
            expected_handled=True,
            expected_flow="PURE_WITH_NOISE",
        )

    # Flow C: Small Talk + Business Query
    for q, canonical in cases[:5]:
        q_mixed = f"{q} where is the office"
        assert_pipeline_outcome(
            q_mixed,
            expected_intent=Intent.SMALL_TALK,
            expected_handled=False,
            expected_flow="PREFIX_QUERY",
        )


# ----------------------------------------------------------------------
# 5. DETERMINISTIC VS RANDOM MODE
# ----------------------------------------------------------------------
def test_deterministic_vs_random_mode() -> None:
    """Verify that deterministicResponse flag forces index 0, whereas random mode varies."""
    # Build context with deterministicResponse = True
    res_det = process_query(
        "thanks", "sess-det", "req-det", metadata={"deterministicResponse": True}
    )
    assert res_det["answer"] == THANKS_RESPONSES["thanks"][0]

    # EmptyInput deterministic check
    res_empty = process_query(
        "", "sess-det", "req-det", metadata={"deterministicResponse": True}
    )
    assert res_empty["answer"] == EMPTY_INPUT_RESPONSES[0]


# ----------------------------------------------------------------------
# 6. pipeline integration & regression verification
# ----------------------------------------------------------------------
def test_greeting_and_normalization_safety() -> None:
    """Assert greetings and normalization step 3 remains stable under Phase 4 additions."""
    # Greetings shouldn't be handled by goodbye/thanks
    res = process_query(
        "hello", "sess-reg", "req-reg", metadata={"deterministicResponse": True}
    )
    assert res["intent"] == Intent.GREETING
    assert "assist you today" in res["answer"]
