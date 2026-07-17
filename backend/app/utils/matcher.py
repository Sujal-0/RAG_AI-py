"""Alias matching utilities.

Provides deterministic longest-phrase searching across configured alias maps.
"""


def find_longest_match(
    tokens: list[str], groups: dict[str, list[str]]
) -> tuple[str, str, list[int]] | None:
    """Find the longest token matching phrase from a canonical alias group.

    Matches can occur anywhere in the token list. Sorting alias terms by length
    ensures longer matching phrases take precedence (e.g., 'good morning' over 'morning').

    Args:
        tokens: Tokenized words of the normalized query.
        groups: Dictionary mapping canonical keys to list of aliases.

    Returns:
        A tuple of (matched_term, canonical_key, matched_indices) if found, else None.
    """
    if not tokens:
        return None

    # Flatten groups into (alias_term, canonical_key, alias_tokens)
    candidates = []
    for canonical, aliases in groups.items():
        for alias in aliases:
            alias_tokens = alias.split(" ")
            candidates.append((alias, canonical, alias_tokens))

    # Sort candidates by number of tokens (descending) to ensure longest-match takes precedence
    candidates.sort(key=lambda x: len(x[2]), reverse=True)

    for term, canonical, term_tokens in candidates:
        term_len = len(term_tokens)
        if term_len > 1:
            # Multi-token phrase scanning
            for i in range(len(tokens) - term_len + 1):
                if tokens[i : i + term_len] == term_tokens:
                    return term, canonical, list(range(i, i + term_len))
        else:
            # Single token lookup
            for i, token in enumerate(tokens):
                if token == term_tokens[0]:
                    return term, canonical, [i]

    return None
