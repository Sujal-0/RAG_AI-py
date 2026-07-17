"""Conversation engines.

Each engine handles exactly one domain of conversation processing.
Engines are executed in strict pipeline order — when an engine handles
a query, the pipeline short-circuits and no further engines run.

Pipeline order:
    Validation → Normalization → EmptyInput → Greeting → Goodbye →
    Thanks → SmallTalk → Gibberish → Alias → CanonicalIntent →
    FastPath → Fallback
"""
