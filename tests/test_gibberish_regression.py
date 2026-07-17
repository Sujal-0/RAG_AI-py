"""Regression test suite for the enhanced layered Gibberish Detection System.

Verifies pure gibberish, mixed queries, spaced/repeated greetings, technical vocab,
names, unknown but meaningful queries, and boundary cases.
"""

from typing import Any
from app.pipeline.process import process_query
from app.pipeline.intents import Intent


def assert_query_intent(query: str, expected_intent: Intent | str) -> dict[str, Any]:
    """Helper to process a query and assert its resolved intent."""
    res = process_query(query, "sess-gibberish-regression", "req-gibberish-regression")
    assert res["success"] is True, f"Failed success check for query: {query}"
    assert res["intent"] == expected_intent, (
        f"Failed intent check on query: {query}. "
        f"Expected: {expected_intent}, Got: {res['intent']}"
    )
    return res


def test_pure_gibberish_inputs() -> None:
    """Verify that pure keyboard smashes and nonsense strings resolve to GIBBERISH."""
    pure_gibberish = [
        "UIAGSS",
        "sahdak",
        "asjk",
        "las",
        "JKSAA",
        "xyzabc123",
        "asdfgqwe",
        "qwertyuiop",
        "sjkdhskjd",
        "poiuytre",
    ]
    for q in pure_gibberish:
        assert_query_intent(q, Intent.GIBBERISH)


def test_mixed_gibberish_queries() -> None:
    """Verify that queries containing a mix of natural language and gibberish resolve to GIBBERISH."""
    mixed_queries = [
        "what is UIAGSS?",
        "who is sahdak?",
        "tell me about asjk",
        "what is las?",
        "give me JKSAA",
        "is UIAGSS located in Pune?",
        "tell me about asjk branches",
    ]
    for q in mixed_queries:
        assert_query_intent(q, Intent.GIBBERISH)


def test_greetings_spacing_and_reps() -> None:
    """Verify greetings with spaces and repeated letters resolve to GREETING."""
    spaced_and_repeated = [
        "h e l l o",
        "heyyyyyaaaa raj",
        "h i i i",
        "g o o d  m o r n i n g",
    ]
    for q in spaced_and_repeated:
        assert_query_intent(q, Intent.GREETING)


def test_technical_vocabulary() -> None:
    """Verify that technical terms and frameworks do NOT trigger gibberish (resolving to FALLBACK or relevant intents)."""
    tech_queries = [
        "what is Python?",
        "tell me about Django and Rust",
        "do you use PHP and Ruby?",
        "explain Cobol and Fortran",
        "how does compiler design work?",
    ]
    for q in tech_queries:
        assert_query_intent(q, Intent.FALLBACK)


def test_person_names() -> None:
    """Verify that standard personal names do NOT trigger gibberish classifications."""
    name_queries = [
        "who is John?",
        "is Aarav working here?",
        "tell me about Sam",
        "does Emily work for you?",
    ]
    for q in name_queries:
        assert_query_intent(q, Intent.FALLBACK)


def test_unknown_meaningful_queries() -> None:
    """Verify that coherent out-of-scope queries resolve to FALLBACK, never GIBBERISH."""
    coherent_queries = [
        "what is the weather today in Boston?",
        "how much does a software engineer make?",
        "can you suggest some books on history?",
        "how to prepare a chocolate cake",
    ]
    for q in coherent_queries:
        assert_query_intent(q, Intent.FALLBACK)


def test_boundary_cases() -> None:
    """Verify boundary cases involving punctuation, numeric strings, and short inputs."""
    # Ok is conversational small talk
    assert_query_intent("ok", Intent.SMALL_TALK)
    
    # Pure punctuation is gibberish
    assert_query_intent("!!!", Intent.GIBBERISH)
    assert_query_intent("????", Intent.GIBBERISH)
    
    # Digit-only is fallback (unsupported content)
    assert_query_intent("12345", Intent.FALLBACK)
