"""Goodbye configurations.

Defines canonical goodbye keys, alias matches, and local ignorable address suffixes.
"""

from app.configs.common import COMMON_NOISE_SUFFIXES

# Maps canonical goodbye keys to list of accepted alias words/phrases
GOODBYE_GROUPS: dict[str, list[str]] = {
    "goodbye": [
        "goodbye",
        "good bye",
        "good-bye",
        "bye bye",
        "bye",
        "byee",
        "byeee",
        "byeeee",
        "byeeeeeee",
        "cya",
        "see you",
        "see ya",
        "see u",
        "take care",
    ],
    "good night": [
        "good night",
        "goodnight",
        "gn",
    ],
    "later": [
        "later",
        "talk to you later",
        "catch you later",
    ],
}

# Suffix address tokens to ignore when evaluating pure goodbye sentences
NOISE_TOKENS: set[str] = COMMON_NOISE_SUFFIXES
