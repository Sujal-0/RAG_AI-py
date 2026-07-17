"""Gratitude configurations.

Defines canonical thanks keys, gratitude alias forms, and noise tokens.
"""

from app.configs.common import COMMON_NOISE_SUFFIXES

# Maps canonical gratitude keys to list of accepted spelling aliases
THANKS_GROUPS: dict[str, list[str]] = {
    "thanks": [
        "thanks",
        "thank you",
        "thankyou",
        "thank u",
        "thx",
        "ty",
        "thanks a lot",
        "many thanks",
        "thankssss",
        "thankyouuu",
        "appreciate it",
        "i appreciate it",
    ]
}

# Suffix address tokens to ignore when evaluating pure thanks sentences
NOISE_TOKENS: set[str] = COMMON_NOISE_SUFFIXES
