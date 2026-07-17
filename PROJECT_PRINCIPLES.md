# Project Principles

This document is the **contract** of the Mobiloitte AI Platform. Every contributor, reviewer, and maintainer must understand and follow these principles.

---

## 1. Deterministic System

Every query must produce the same result every time. There is no randomness, no probability, no "it depends." Given the same input, the same output must always be returned.

**Violation example:** Using `random.choice()` to select a response.
**Correct approach:** Always return the first response in the configured list (or select deterministically based on input).

## 2. Stateless Architecture

Every request is independent. The system has no memory of previous queries, no session history, no conversation context carried between requests. Each request creates a fresh `ConversationContext`, processes it through the pipeline, and discards it.

**Violation example:** Storing user preferences between requests.
**Correct approach:** Treat every request as if it's the first.

## 3. Configuration-Driven Behavior

Engines contain **logic**. Configs contain **data**. To change what the system recognizes or responds with, edit configuration files — never engine code.

**Violation example:** Hardcoding greeting words inside `greeting.py`.
**Correct approach:** Define greeting words in `configs/greetings.py`, import them in the engine.

## 4. Single Responsibility Per Engine

Each engine handles exactly one domain of conversation processing. Engines do not know about each other. They do not call each other (with rare, documented exceptions).

**Violation example:** GreetingEngine also checking for goodbye phrases.
**Correct approach:** GreetingEngine handles greetings only; GoodbyeEngine handles goodbyes.

## 5. No AI Decision Making

This platform does not use artificial intelligence, machine learning, large language models, embeddings, vector databases, or any probabilistic reasoning system. Every classification is based on deterministic pattern matching, keyword lookup, and threshold-based heuristics — all defined in configuration.

## 6. No Fuzzy Matching

The system uses exact string matching, regex patterns, and deterministic heuristics. There is no Levenshtein distance, no similarity scoring, no approximate matching.

## 7. Explainable Pipeline

Every decision the system makes must be traceable. The execution trace log records which engine handled the query, what rule matched, and why. A developer reading the trace should be able to explain the system's behavior line by line.

## 8. Production Coding Standards

- Every file has a docstring
- Every function has type hints
- No dead code
- No placeholder TODO comments
- No unnecessary abstractions
- Code reads like prose written by a senior Python engineer
- Every line of code justifies its existence

## 9. Pipeline Order Is Sacred

The pipeline execution order defines business behavior. It must not change unless explicitly approved:

```
Validation → Normalization → EmptyInput → Greeting → Goodbye →
Thanks → SmallTalk → Gibberish → Alias → CanonicalIntent →
FastPath → Fallback
```

## 10. Pythonic Design

This is a Python project, not JavaScript translated to Python. We prefer:
- Modules over classes
- Functions over methods
- Composition over inheritance
- Simple over clever
- Explicit over implicit
- Flat over nested
