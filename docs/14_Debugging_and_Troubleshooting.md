# Chapter 14: Debugging and Troubleshooting Guide

## Purpose
This document catalogs common errors, system misconfigurations, and known bugs that you may encounter when maintaining the Mobiloitte AI Knowledge Assistant. It provides exact reproduction steps and the immediate solution.

---

## 1. Database & pgvector Errors

### 1.1 `psycopg2.errors.UndefinedObject: type "vector" does not exist`
- **Cause:** You started the FastAPI app, but the PostgreSQL database does not have the `pgvector` extension installed.
- **Solution:** Connect to your Postgres instance via `psql` and run:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
  Then restart the FastAPI backend.

### 1.2 `OperationalError: connection refused`
- **Cause:** The database connection string in `.env` (`DATABASE_URL`) is incorrect, or the Postgres container is not running.
- **Solution:** Verify your `.env` file. If using Docker, run `docker ps` to ensure the Postgres container is up.

---

## 2. LLM & Generation Errors

### 2.1 `503 UNAVAILABLE: This model is currently experiencing high demand.`
- **Cause:** Google's Gemini API is overloaded. 
- **Symptoms:** The UI might show the response slightly slower than usual. The backend logs will show `Tenacity` retrying.
- **Solution:** None required on your end. The system's `CircuitBreaker` and `ExtractiveAnswerGenerator` will automatically catch this and serve a fallback answer to the user.

### 2.2 `FinishReason.MAX_TOKENS` causing cut-off answers
- **Cause:** Passing `max_output_tokens` in the Gemini configuration can sometimes cause the `google-genai` SDK to aggressively truncate the response mid-sentence.
- **Solution:** Remove `max_output_tokens` from `app/engines/llm_generator.py`. Control output length via the System Prompt instead (e.g., "Be concise").

### 2.3 Responses contain mechanical `[1]` tags instead of natural text
- **Cause:** The system prompt is too rigid.
- **Solution:** Update `SYSTEM_PROMPT` in `llm_generator.py` to say "Seamlessly integrate facts into your prose without robotic brackets" and remove the bullet-point enforcement.

---

## 3. Embedding & Ingestion Errors

### 3.1 `[WinError 1114] A dynamic link library (DLL) initialization routine failed`
- **Cause:** A known issue on Windows where `torch` or `sentence-transformers` fails to load the C++ underlying libraries, usually due to missing Visual C++ Redistributables or an invalid `torch` CPU wheel.
- **Symptoms:** The `EmbeddingService` will throw a `RAG_EMBEDDING_FAILED` error, and the backend will fall back to `DummyModel`.
- **Solution:** Reinstall `torch` strictly for CPU:
  ```bash
  pip uninstall torch torchvision torchaudio
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```

### 3.2 "DummyModel" is being used for Vector Search
- **Cause:** Similar to the above. If the `SentenceTransformer` fails to initialize in `main.py`, the system falls back to a DummyModel so the app doesn't crash.
- **Symptoms:** The bot will give terribly inaccurate answers, because the DummyModel generates random math vectors based on string hashing instead of semantic meaning.
- **Solution:** Check the startup logs to see why `SentenceTransformer` failed. Fix the dependency issue and restart Uvicorn.

---

## 4. Pipeline Routing Issues

### 4.1 FastPath is stealing RAG queries
- **Cause:** A FastPath rule for "services" is triggering when the user asks "What are our services?", but you have an uploaded document detailing your services.
- **Solution:** Update the `FAST_PATH_RULES` in `configs.validation` and set `is_document_aware=True` for that specific rule. The FastPath engine will then check the vector search first before answering locally.

### 4.2 Bot answers "I don't know" to everything
- **Cause:** The Evidence Confidence Gate is set too high.
- **Solution:** In `rag_engine.py`, locate the `reject_threshold`. If it is set to `0.50`, lower it to `0.35`. If it still fails, check the `Developer Mode` UI to see if the chunks being retrieved actually match the question.

---

## 5. UI / Frontend Issues

### 5.1 Chat auto-scroll stops working
- **Cause:** The user manually scrolled up to read past messages, which sets `userHasScrolledUp` to true in `App.jsx`.
- **Solution:** This is intended behavior so we don't rip the screen away from a reading user. They just need to scroll back to the bottom.

### 5.2 "Failed to connect to the backend server"
- **Cause:** The FastAPI server is down, or CORS is blocking the request.
- **Solution:** Ensure Uvicorn is running. Check `main.py` to ensure `CORSMiddleware` allows origins from `http://localhost:5173`.
