"""Text processing and normalization utilities.

Exposes pure functions for normalizing user queries through a strict
13-step deterministic pipeline.
"""

import re
import unicodedata
import difflib

from app.configs.greetings import GREETING_GROUPS
from app.configs.normalization import SPELLING_CORRECTIONS
from app.configs.common import TECHNICAL_VOCABULARY, LOCATIONS, COMMON_COMPANY_WORDS


def normalize_unicode(text: str) -> str:
    """Apply Unicode NFKC normalization."""
    return unicodedata.normalize("NFKC", text)


def remove_zero_width(text: str) -> str:
    """Remove zero-width spaces and invisible formatting characters."""
    return re.sub(r"[\u200B-\u200D\uFEFF]", "", text)


def normalize_whitespace(text: str) -> str:
    """Convert tabs, newlines, and carriage returns to standard spaces."""
    return re.sub(r"[\t\r\n]", " ", text)


def collapse_spaces(text: str) -> str:
    """Replace multiple consecutive spaces with a single space."""
    return re.sub(r"\s+", " ", text)


def remove_emojis(text: str) -> str:
    """Remove standard emoji characters from the text string."""
    emoji_pattern = re.compile(
        r"[\U0001f000-\U0001faf6\u2600-\u27bf]",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def normalize_punctuation(text: str) -> str:
    """Standardize punctuation and replace contractions/quotes."""
    # Strip smart quotes and apostrophes to preserve standard contractions (e.g. what's -> whats)
    text = re.sub(r"[’'‘]", "", text)
    # Replace other punctuation with spaces to avoid joining adjacent words
    text = re.sub(r"[?,.!;:()\-+=\[\]{}@#$%^&*~_/\\|<>]", " ", text)
    return text


def remove_symbols(text: str) -> str:
    """Ensure only alphanumeric characters and spaces remain."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", text)


def compress_greeting_letters(text: str) -> str:
    """Compress repeated letters in greeting words only."""
    text = re.sub(r"\bh+e+y+a*(?=[0-9\s]|$)", "hey", text)
    text = re.sub(r"\bh+e+l+l+o+(?=[0-9\s]|$)", "hello", text)
    text = re.sub(r"\bh+e+l+o+(?=[0-9\s]|$)", "hello", text)
    text = re.sub(r"\bh+i+e*(?=[0-9\s]|$)", "hi", text)
    text = re.sub(r"\bh+y+(?=[0-9\s]|$)", "hi", text)
    text = re.sub(r"\bg+o+o+d+\s*m+o+r+n+i+n+g+(?=[0-9\s]|$)", "good morning", text)
    text = re.sub(r"\bg+o+o+d+\s*e+v+e+n+i+n+g+(?=[0-9\s]|$)", "good evening", text)
    text = re.sub(
        r"\bg+o+o+d+\s*a+f+t+e+r+n+o+o+n+(?=[0-9\s]|$)", "good afternoon", text
    )
    text = re.sub(r"\bg+o+o+d+\s*n+i+g+h+t+(?=[0-9\s]|$)", "good night", text)
    text = re.sub(r"\bm+o+r+n+i+n+g+(?=[0-9\s]|$)", "morning", text)
    text = re.sub(r"\bn+i+g+h+t+(?=[0-9\s]|$)", "night", text)
    text = re.sub(r"\bg+m+n+g+(?=[0-9\s]|$)", "gmng", text)
    text = re.sub(r"\bg+m+n+(?=[0-9\s]|$)", "gm", text)
    text = re.sub(r"\bg+m+(?=[0-9\s]|$)", "gm", text)
    text = re.sub(r"\bg+a+(?=[0-9\s]|$)", "ga", text)
    text = re.sub(r"\bg+e+(?=[0-9\s]|$)", "ge", text)
    text = re.sub(r"\bg+n+(?=[0-9\s]|$)", "gn", text)
    return text


def apply_spelling_corrections(text: str) -> str:
    """Correct misspelled greetings using the static corrections dictionary."""
    for wrong, right in SPELLING_CORRECTIONS.items():
        pattern = rf"\b{wrong}(?=[0-9\s]|$)"
        text = re.sub(pattern, right, text)
    return text


def strip_greeting_numbers(text: str) -> str:
    """Strip numbers immediately following configured greeting words (e.g. hi1 -> hi)."""
    # Gather all candidate greeting terms to protect against number stripping elsewhere
    greeting_words = set()
    for aliases in GREETING_GROUPS.values():
        greeting_words.update(aliases)
    greeting_words.update(SPELLING_CORRECTIONS.keys())

    if not greeting_words:
        return text

    # Sort descending by length so longer matches take precedence
    sorted_words = sorted(list(greeting_words), key=len, reverse=True)
    escaped_words = [re.escape(w).replace(r"\ ", r"\s+") for w in sorted_words]

    # Pattern: word followed by optional space then digits
    regex_pattern = r"\b(" + "|".join(escaped_words) + r")\s*[0-9]+\b"
    return re.sub(regex_pattern, r"\1", text)


def merge_spaced_characters(text: str) -> str:
    """Merge spaced letters if and only if every token is exactly one alphabetic character (or a single character repeated)."""
    if not text:
        return text
    tokens = [t for t in text.split(" ") if t]
    if tokens and all(len(set(t)) == 1 and t.isalpha() for t in tokens):
        return "".join(tokens)
    return text


def tokenize(text: str) -> list[str]:
    """Tokenize text into a list of words using space delimiter."""
    if not text:
        return []
    return [t for t in text.split(" ") if t]


def normalize_text(text: str) -> str:
    """Orchestrate the 13-step text normalization sequence.

    Args:
        text: Raw input query text string.

    Returns:
        Pruned, normalized copy of the text.
    """
    if not text:
        return ""

    # 1. Unicode normalization (NFKC)
    t = normalize_unicode(text)

    # 2. Lowercase conversion
    t = t.lower()

    # 3. Remove zero-width characters
    t = remove_zero_width(t)

    # 4. Normalize tabs/newlines
    t = normalize_whitespace(t)

    # 5. Collapse whitespace
    t = collapse_spaces(t)

    # 6. Remove emojis
    t = remove_emojis(t)

    # 7. Normalize punctuation
    t = normalize_punctuation(t)

    # 8. Remove unsupported symbols
    t = remove_symbols(t)

    # 9. Collapse whitespace again
    t = collapse_spaces(t)

    # 9.5 Merge spaced characters (preprocessing stage for spaced greetings)
    t = merge_spaced_characters(t)

    # 10. Compress repeated greeting letters
    t = compress_greeting_letters(t)

    # 11. Apply spelling corrections
    t = apply_spelling_corrections(t)

    # 12. Strip greeting suffix numbers
    t = strip_greeting_numbers(t)

    # 13. Final trim
    return t.strip()


def fuzzy_correct_tokens(tokens: list[str]) -> list[str]:
    """Corrects minor spelling mistakes in tokens using a known vocabulary."""
    if not tokens:
        return []

    # Assemble known critical vocabulary
    static_vocab = {
        "policy", "leave", "vacation", "holiday", "work", "office", "hybrid", "wfh", "home",
        "benefit", "benefits", "salary", "bonus", "insurance", "medical", "sick", "casual",
        "probation", "onboarding", "recruitment", "career", "careers", "job", "jobs", "intern",
        "internship", "security", "zero", "trust", "mfa", "auth", "authentication", "compliance",
        "iso27001", "iso", "cybersecurity", "engineering", "hr", "human", "resources", "department",
        "departments", "structure", "ceo", "founder", "founded", "history", "vision", "mission",
        "value", "values", "culture", "training", "upskill", "support", "email", "phone",
        "service", "services", "product", "products", "technologies", "tech", "stack",
        "pune", "delhi", "noida", "london", "singapore", "headquarters", "address",
        "handbook", "employee", "conduct", "rules", "guidelines", "section", "clause", "page",
        "document", "documents", "contract", "contracts", "agreement", "agreements",
        "developer", "manager", "engineer", "software", "development", "training", "timings",
        "timing", "hours", "payroll", "promotion", "travel", "reimbursement", "reimbursements",
        "feedback", "performance", "review", "reviews", "appraisal",
        "architecture", "microservices", "kafka", "rabbitmq", "oauth", "jwt",
        "devops", "api", "documentation", "swagger", "rest", "graphql",
        "what", "where", "who", "why", "how", "when", "tell", "about", "info",
        "details", "information", "find", "explain", "summarize", "list", "show"
    }
    
    # Merge imported common words
    full_vocab = static_vocab.union(TECHNICAL_VOCABULARY).union(LOCATIONS).union(COMMON_COMPANY_WORDS)
    vocab_list = list(full_vocab)
    
    corrected_tokens = []
    for t in tokens:
        if t in full_vocab:
            corrected_tokens.append(t)
            continue
            
        # Try to find a close match. Only correct if highly confident (e.g. >= 0.8)
        # For very short words, avoid aggressive correction to prevent false positives
        cutoff = 0.85 if len(t) < 5 else 0.75
        matches = difflib.get_close_matches(t, vocab_list, n=1, cutoff=cutoff)
        
        if matches:
            corrected_tokens.append(matches[0])
        else:
            corrected_tokens.append(t)
            
    return corrected_tokens
