# Mobiloitte AI Platform — Python Edition

A deterministic, configuration-driven Conversation Intelligence Platform built with Python, FastAPI, and React.

## What This Is

This is a **rule-driven conversation engine** that processes user queries through a deterministic pipeline. Every input produces the same output — always. No AI, no ML, no fuzzy matching.

## What This Is NOT

- Not a chatbot
- Not an LLM application
- Not RAG
- Not OpenAI / Gemini / Claude
- Not fuzzy or probabilistic

## Tech Stack

### Backend
| Tool | Purpose |
|------|---------|
| Python 3.12+ | Runtime |
| FastAPI | Web framework |
| Pydantic v2 | Data validation & models |
| uv | Package manager |
| pytest | Testing |
| ruff | Linting |
| black | Formatting |

### Frontend
| Tool | Purpose |
|------|---------|
| React | UI framework |
| Vite | Build tool |
| Tailwind CSS v4 | Styling |
| shadcn/ui | Component library |
| Zustand | State management |
| Framer Motion | Animations |

## Quick Start

### Backend
```bash
cd backend
uv sync --all-extras
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Run Tests
```bash
cd backend
uv run pytest ../tests/ -v
```

### Lint & Format
```bash
cd backend
uv run ruff check app/
uv run black --check app/
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP route handlers
│   │   ├── pipeline/     # Context, result, base engine, executor
│   │   ├── engines/      # One module per conversation engine
│   │   ├── configs/      # Data-only configuration modules
│   │   └── utils/        # Pure utility functions
│   └── pyproject.toml
├── frontend/             # React + Vite application
├── tests/                # pytest test suite
└── docs/                 # Project documentation
```

## Pipeline

Every query flows through these engines in strict order:

```
Validation → Normalization → EmptyInput → Greeting → Goodbye →
Thanks → SmallTalk → Gibberish → Alias → CanonicalIntent →
FastPath → Fallback
```

When an engine handles a query, the pipeline stops. No further engines run.

## Intents

The system classifies every query into exactly one intent:

| Intent | Meaning |
|--------|---------|
| `GREETING` | User is greeting |
| `SMALL_TALK` | Goodbye, thanks, how are you, etc. |
| `COMPANY_INTENT` | Business question with a known answer |
| `GIBBERISH` | Meaningless or random input |
| `FALLBACK` | Understandable but out-of-scope |

## License

Proprietary — Mobiloitte Technologies India Pvt. Ltd.
