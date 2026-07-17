"""Configuration modules.

All behavior-defining data lives here. Engines contain only logic;
configurations contain only data. This separation ensures behavior
can be changed without modifying engine code.

Modules:
    - validation: Request validation constraints
    - normalization: Spelling corrections and text cleanup rules
    - greetings: Greeting words, categories, and responses
    - goodbyes: Goodbye patterns and responses
    - thanks: Gratitude patterns and responses
    - small_talk: Conversational patterns and responses
    - gibberish: Detection thresholds, spam rules, natural language words
    - alias: Typo corrections and synonym mappings
    - intent: Intent identifiers and regex trigger patterns
    - knowledge: Corporate knowledge base with approved answers
    - fallback: Default responses for unmatched and empty queries
"""
