"""Unit tests for the 13-step text normalization pipeline."""

from app.utils.text import (
    apply_spelling_corrections,
    collapse_spaces,
    compress_greeting_letters,
    normalize_punctuation,
    normalize_text,
    normalize_unicode,
    normalize_whitespace,
    remove_emojis,
    remove_symbols,
    remove_zero_width,
    strip_greeting_numbers,
)


def test_step_1_unicode_normalization() -> None:
    """Validate NFKC Unicode decomposition/composition formatting."""
    # Fullwidth latin characters to standard characters
    assert normalize_unicode("Ｈｅｌｌｏ") == "Hello"


def test_step_2_lowercase_conversion() -> None:
    """Validate case mappings."""
    assert "HELLO".lower() == "hello"
    assert "HeLLo".lower() == "hello"


def test_step_3_remove_zero_width() -> None:
    """Verify stripping zero-width space characters."""
    raw = "h\u200be\u200cl\u200do\ufeff"
    assert remove_zero_width(raw) == "helo"


def test_step_4_normalize_whitespace() -> None:
    """Verify tabs and carriage returns translate to standard spaces."""
    assert normalize_whitespace("hello\tworld\n") == "hello world "


def test_step_5_collapse_whitespace() -> None:
    """Verify collapsing multiple consecutive spaces."""
    assert collapse_spaces("hello   world") == "hello world"


def test_step_6_remove_emojis() -> None:
    """Ensure standard emojis are stripped out completely."""
    assert remove_emojis("hello 👋 how are you 😊") == "hello  how are you "


def test_step_7_normalize_punctuation() -> None:
    """Ensure smart quotes map nicely and punctuation becomes spaces."""
    assert normalize_punctuation("what’s up?") == "whats up "
    assert normalize_punctuation("hello!!!") == "hello   "


def test_step_8_remove_symbols() -> None:
    """Ensure only letters, numbers, and spaces survive."""
    assert remove_symbols("hello   world  @#$") == "hello   world  "


def test_step_10_compress_repeated_letters() -> None:
    """Verify only configured greeting words are compressed."""
    assert compress_greeting_letters("hiii") == "hi"
    assert compress_greeting_letters("heyyyy") == "hey"
    assert compress_greeting_letters("hellooooo") == "hello"
    assert compress_greeting_letters("good morningggg") == "good morning"
    # Non-greeting words must never be compressed
    assert compress_greeting_letters("sweet") == "sweet"
    assert compress_greeting_letters("look") == "look"


def test_step_11_apply_spelling_corrections() -> None:
    """Verify typo corrections dictionary works as configured."""
    assert apply_spelling_corrections("helo") == "hello"
    assert apply_spelling_corrections("gmng") == "good morning"


def test_step_12_strip_greeting_numbers() -> None:
    """Ensure trailing numbers are removed from greeting words only."""
    assert strip_greeting_numbers("hi123") == "hi"
    assert strip_greeting_numbers("hello999") == "hello"
    assert strip_greeting_numbers("gm2026") == "gm"
    # Non-greeting words must keep numbers
    assert strip_greeting_numbers("room101") == "room101"
    assert strip_greeting_numbers("office2026") == "office2026"


def test_full_normalization_pipeline() -> None:
    """Exhaustive check on the full normalize_text orchestration."""
    assert normalize_text("   Ｈｅｌｌｏooo123!!! 👋   ") == "hello"
    assert normalize_text("what’s the office address?") == "whats the office address"
    assert (
        normalize_text("hello sujal, where is the office?")
        == "hello sujal where is the office"
    )
    assert normalize_text("GM123 Bro!!!") == "gm bro"
    assert normalize_text("   hiiiiii333 sir 😊   ") == "hi sir"
    assert normalize_text("goodmorning!!!!!!!!!!") == "good morning"
    assert normalize_text("Hello@@@ Everyone") == "hello everyone"
    assert normalize_text("heya") == "hey"
    assert normalize_text("hiiie") == "hi"
    assert normalize_text("heya sujal") == "hey sujal"
    assert normalize_text("hiiie raj") == "hi raj"
    assert normalize_text("hy") == "hi"
