# Chapter 2: Folder Structure & Chapter 22: Codebase Walkthrough

## Purpose
This document is the ultimate code-reading guide. It explains exactly how the codebase is structured, why each folder exists, and breaks down every single important file line-by-line in terms of its purpose, input, output, and dependencies.

If you are a new engineer joining the team, read this file before opening your IDE.

---

## 1. High-Level Folder Structure

```text
Mobiloitte-AI-Platform-Python/
├── frontend/                 # React UI Application
│   ├── src/                  # React Source Code
│   │   ├── App.jsx           # Main UI, Chat Console, Dev Mode
│   │   ├── index.css         # Tailwind Styling
│   │   └── main.jsx          # React DOM Mount
│   └── package.json          # Node Dependencies
│
├── backend/                  # FastAPI Application
│   ├── app/                  # Core Business Logic
│   │   ├── api/              # API Routers (Endpoints)
│   │   ├── chunkers/         # Document Semantic Chunking
│   │   ├── configs/          # Regex Rules, Intents, Aliases
│   │   ├── core/             # Settings & Environment variables
│   │   ├── embeddings/       # Sentence Transformers wrapper
│   │   ├── engines/          # All Pipeline Engines (RAG, FastPath, etc)
│   │   ├── models/           # SQLAlchemy Database Schemas
│   │   ├── pipeline/         # Orchestrator & Context
│   │   ├── services/         # Utility services (DB connections)
│   │   ├── utils/            # Shared helpers
│   │   └── main.py           # FastAPI Application Entry Point
│   ├── .env                  # Secrets and Configs
│   ├── alembic/              # Database Migrations
│   └── requirements.txt      # Python Dependencies
```

### Why this design was chosen:
The backend follows a strict **Domain-Driven Design (DDD)** combined with a **Micro-Kernel Architecture**. The `pipeline/` acts as the kernel, while the `engines/` act as plugins. This completely isolates routing logic from text-generation logic from database logic.

---

## 2. Code Reading Guide: Where to Start?

Do not read files alphabetically. Read them in the order data flows through the system.

1. **`backend/app/main.py`**: The application bootstrapper. Sets up CORS, Database connections, and registers API routers.
2. **`backend/app/api/chat.py`**: The endpoint `POST /chat`. Defines the Pydantic schema and initiates the Pipeline.
3. **`backend/app/pipeline/process.py`**: The Orchestrator. See how engines are chained together.
4. **`backend/app/engines/decision.py`**: The Brain. See how queries get classified into Intents.
5. **`backend/app/engines/rag_engine.py`**: The core RAG logic (Vector Search + LLM invocation).
6. **`backend/app/engines/llm_generator.py`**: The Gemini API wrapper and prompt builder.

---

## 3. Every Important File Walkthrough

### `backend/app/main.py`
- **Purpose:** Starts the Uvicorn web server and mounts the FastAPI application.
- **Key Functions:** `lifespan()` handles application startup and shutdown. It tests the PostgreSQL connection and loads the MiniLM embedding model into RAM before accepting the first HTTP request.
- **Dependencies:** `fastapi`, `sqlalchemy`, `app.api`.

### `backend/app/api/chat.py`
- **Purpose:** Receives user messages from the React frontend.
- **Key Classes:** `ChatRequest` (Pydantic model validating input), `ChatResponse` (Output schema including telemetry).
- **Flow:** Takes JSON, calls `process_query()`, awaits the result, and returns JSON.

### `backend/app/configs/validation.py`
- **Purpose:** The rulebook for the Decision Engine and FastPath.
- **Contents:**
  - `GREETING_PATTERNS`: Regex for "hello", "hi".
  - `BUSINESS_TOPIC_KEYWORDS`: Lists of words like "policy", "salary", "leave".
  - `FAST_PATH_RULES`: Dictionaries mapping exact questions to deterministic answers.
- **Why this design was chosen:** Storing rules in a central config file means we don't have to hunt through 50 Python files to change a regex pattern.

### `backend/app/configs/alias.py`
- **Purpose:** Acronym resolution.
- **Contents:** `ALIAS_MAP = {"pto": "Paid Time Off", "wfh": "Work From Home"}`.

### `backend/app/pipeline/process.py`
- **Purpose:** Executes the engines in order.
- **Key Functions:** `process_query()`.
- **Input:** Raw query string.
- **Output:** `PipelineResult` object containing the final answer and telemetry trace.

### `backend/app/engines/decision.py`
- **Purpose:** Classifies the query intent.
- **Key Method:** `process(context)`. It applies regex patterns from `configs.validation`. If a pattern matches, it sets `context.intent` (e.g., `GREETING`).
- **Dependencies:** `re` (Regex), `configs.validation`.

### `backend/app/engines/fast_path.py`
- **Purpose:** Instantly answers known facts.
- **Key Logic:** It reads `FAST_PATH_RULES`. If a match is found, it evaluates `is_document_aware`. If the user asks about a topic that is highly likely to be found in the uploaded documents, it skips itself and lets the RAG engine handle it. Otherwise, it sets `handled=True` and returns the hardcoded answer.

### `backend/app/engines/rag_engine.py` (The Heart)
- **Purpose:** Vector Search and generation.
- **Key Methods:** `process(context)`.
- **Flow:**
  1. Calls `EmbeddingService` to get vectors.
  2. Executes complex SQL Hybrid Search.
  3. Evaluates `Evidence Confidence Gate`. If max score < 0.35, throws error.
  4. Calls `LLMGenerator`.
  5. Catches API crashes and falls back to `ExtractiveAnswerGenerator`.
- **Dependencies:** `sqlalchemy`, `app.embeddings`, `app.engines.llm_generator`.

### `backend/app/engines/llm_generator.py`
- **Purpose:** Talks to Google Gemini.
- **Key Classes:** `GeminiAnswerGenerator`.
- **Key Variables:** `SYSTEM_PROMPT`. This multi-line string strictly commands the LLM not to hallucinate, to be concise, and to integrate facts seamlessly.
- **Resilience:** Uses `@retry` from the `tenacity` library to back off exponentially if the API hits a 429 or 503 error.

### `backend/app/embeddings/embedding_service.py`
- **Purpose:** Generates 384D vectors.
- **Key Classes:** `EmbeddingService`. It loads `sentence-transformers/all-MiniLM-L6-v2` globally so it doesn't have to be re-downloaded or loaded into RAM on every request.

### `backend/app/chunkers/semantic_chunker.py`
- **Purpose:** Breaks massive PDFs into searchable paragraphs.
- **Key Logic:** Splits on `\n\n` (paragraphs). If a paragraph is still too long, splits on `. ` (sentences). Merges small chunks together until they hit a threshold of ~500 characters. Extracts uppercase lines as `headings`.

### `backend/app/models/document.py`
- **Purpose:** SQLAlchemy ORM definitions for the database.
- **Classes:** `Document` (file metadata) and `DocumentChunk` (text and pgvector column).
- **Dependencies:** `pgvector.sqlalchemy.Vector`.

### `frontend/src/App.jsx`
- **Purpose:** The entire React UI.
- **Key Features:** Chat rendering, API polling for documents, and the massive `DebugTrace` component which parses the `debugInfo` JSON from the backend and renders the execution timeline, similarity scores, and routing decisions.

---

## 4. Manager Interview Questions

**Q: If we hire a Junior Developer, how long will it take them to understand this code?**
*Answer:* Less than a day. Because we strictly separated concerns (Engines don't talk to the Database directly, the Database doesn't talk to the LLM directly), a junior can be assigned to build a new `WeatherEngine` without ever needing to understand how pgvector or Gemini works. They just create a class, add it to the `PipelineRegistry`, and return an `EngineResult`.

**Q: Are there any circular dependencies?**
*Answer:* No. The architecture flows top-down. The API calls the Pipeline. The Pipeline calls the Engines. The Engines call the Services (DB/LLM). Services never call Engines. This makes the codebase extremely testable and immune to infinite import loops.
