# Architecture — Mobiloitte AI Platform (Python Edition)

## 1. Overview

The Conversation Intelligence Platform processes incoming user queries statelessly and deterministically. Every query traverses an explicit pipeline of specialized engines in a strict execution sequence. If an engine handles the query, execution short-circuits immediately.

This platform does not utilize AI/ML libraries, LLMs, fuzzy matching, or database persistence. It is built entirely on deterministic rules and data configurations, ensuring 100% explainability.

---

## 2. Design Principles

1. **Determinism** — The same input always produces the exact same classification and response.
2. **Configuration-Driven** — Engines encapsulate matching logic; raw data (lists, regexes, answers) is isolated in configuration files.
3. **Stateless** — Each query starts a fresh context. There is no conversation memory, caching, or session tracking.
4. **Pythonic Simplicity** — Avoids Java-style registries, service layers, and factory classes. Prefers modules, pure functions, and standard Pydantic models.

---

## 3. Directory Layout & Module Responsibilities

```
backend/
├── app/
│   ├── main.py              # Application entry point, configures CORS and middleware
│   ├── api/
│   │   ├── health.py        # GET / - Liveness health probe
│   │   └── chat.py          # POST /chat (Query validation & execution dispatch)
│   ├── core/
│   │   └── settings.py      # App configurations managed via pydantic-settings
│   ├── middleware/
│   │   └── request_id.py    # Request ID middleware injecting tracking correlation IDs
│   ├── pipeline/
│   │   ├── base.py          # BaseEngine Abstract Base Class contract definition
│   │   ├── context.py       # ConversationContext state carrier model
│   │   ├── result.py        # EngineResult execution outcome model
│   │   ├── pipeline.py      # Explicit static PIPELINE execution sequence
│   │   ├── executor.py      # run_pipeline() driver executing sequential loops
│   │   └── process.py       # process_query() orchestrator and build_response()
│   ├── engines/             # Pipeline engines (12 placeholders returning handled=False)
│   ├── configs/             # Configuration modules containing logic data
│   └── utils/
│       └── logger.py        # Standardized request-id tracked logger utility
```

---

## 4. Lifecycle Mappings

### Request Lifecycle
1. **Middleware Entry**: Client sends `POST /api/v1/chat`. `RequestIdMiddleware` intercepts it, extracts `X-Request-ID` (or generates a fresh UUID), binds it to `request.state.request_id`, and sets the response headers.
2. **API Endpoint Router**: `chat_endpoint` validates input formats via `ChatRequest` (length checks, session ID regex rules).
3. **Stateless Processing**: Route handler fetches `request_id` and invokes `process_query(query, session_id, request_id)`.
4. **Response Serialization**: The processed `ConversationContext` is passed to `build_response()` mapping standard payload JSON.
5. **Middleware Exit**: Header `X-Request-ID` is written to the HTTP response.

```
Client  ──[POST /chat]──>  RequestIdMiddleware (Generates request_id)
                                    │
                                    ▼
                             Chat Endpoint (Validates ChatRequest schema)
                                    │
                                    ▼
                              process_query()
                                    │
                                    ▼
                              run_pipeline() ──[Validation -> Fallback]
                                    │
                                    ▼
                              build_response()
                                    │
                                    ▼
Client  <──[JSON + Header]──  Response returned to Client
```

### Context Lifecycle
- Created at the entry of `process_query` using the validated request attributes.
- Traverses the pipeline by reference through `run_pipeline(context)`.
- Modifies properties inside each executing engine (e.g. `normalized_query`, `intent`, `response`, `trace`).
- Transformed by `build_response` into a JSON dictionary, then garbage collected.

### Engine Lifecycle
- Defined as subclasses of `BaseEngine` in `app.engines.*`.
- Abstract properties enforce `name` implementation and the `execute(context: ConversationContext) -> EngineResult` signature.
- Instantiated statically once inside `app.pipeline.pipeline.PIPELINE`.
- Expose zero execution side-effects — logic is purely deterministic and stateless.

---

## 5. Pipeline Ordering

The pipeline sequence is explicitly hardcoded in `app/pipeline/pipeline.py`. The engines run in this exact order:

1. **Validation** — Request payload length, type, and sessionId integrity check.
2. **Normalization** — Collapsing whitespace, casing, zero-width chars, and removing emojis.
3. **EmptyInput** — Intercepting blank or whitespace-only inputs.
4. **Greeting** — Greeting word recognition across multiple languages.
5. **Goodbye** — Farewell phrase detection.
6. **Thanks** — Gratitude phrase checks.
7. **SmallTalk** — General chit-chat (name, capabilities, status).
8. **Gibberish** — Keyboard smash, vowel ratio anomalies, and Shannon entropy analysis.
9. **Alias** — Synonym mappings and spelling corrections.
10. **CanonicalIntent** — Intent classification scoring (regex and keyword density).
11. **FastPath** — Retrieval of corporate knowledge base answers.
12. **Fallback** — Catch-all handler for understandable out-of-scope queries.

---

## 6. Execution Trace

For diagnostic transparency, each engine execution adds a trace log to `ConversationContext.trace` containing:
- `engine` (name)
- `handled` (boolean)
- `reasonCode` (string)
- `executionTimeMs` (float duration)

An application log is also pushed detailing these standard properties alongside the `request_id`.

## 7. Diagnostics Endpoint

When `DEBUG=True` is set in global configurations, the application registers `GET /api/v1/debug/pipeline` exposing the exact ordered sequence of engines. This endpoint is forbidden in production environments.
