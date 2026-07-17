"""Deterministic and random response selection helpers.

Evaluates client metadata context flags to route either index-0 fallback
or randomized responses.
"""

import random
from typing import Any


def select_response(
    key: str, responses_dict: dict[str, list[str]], context: Any
) -> str:
    """Resolve a response string from key options using metadata trace configuration.

    If context metadata specifies 'deterministicResponse' is True, the first index
    is consistently selected. Otherwise, a random candidate is selected.

    Args:
        key: Canonical lookup string.
        responses_dict: Dictionary mapping canonical keys to list of string choices.
        context: Active ConversationContext instance.

    Returns:
        Resolved response text string.
    """
    options = responses_dict.get(key, ["Hello!"])
    deterministic = False
    if hasattr(context, "metadata") and isinstance(context.metadata, dict):
        deterministic = context.metadata.get("deterministicResponse", False)

    if deterministic:
        return options[0]

    return random.choice(options)


def format_greeting_with_name(response: str, key: str, name: str) -> str:
    """Format greeting response to include person name after greeting phrase."""
    import re
    greeting_starts = [
        "hi there", "sat sri akal", "good morning", "good afternoon",
        "good evening", "good night", "hello", "hi", "hey", "namaste",
        "vanakkam", "adaab", "hola", "bonjour", "ciao", "hallo", "konnichiwa"
    ]
    for start in greeting_starts:
        pattern = rf"^({re.escape(start)})([!,])"
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            matched_str = match.group(1)
            punctuation = match.group(2)
            return response.replace(match.group(0), f"{matched_str} {name}{punctuation}", 1)

    # Fallback to matching first word
    match = re.search(r"^(\w+)([!,])", response)
    if match:
        matched_str = match.group(1)
        punctuation = match.group(2)
        return response.replace(match.group(0), f"{matched_str} {name}{punctuation}", 1)

    return response

