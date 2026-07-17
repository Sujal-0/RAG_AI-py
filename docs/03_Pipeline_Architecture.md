# Chapter 5: Pipeline Architecture

## Purpose
The AI Knowledge Assistant does not rely on a monolithic block of `if/else` statements. Instead, it utilizes a highly scalable and decoupled **Pipeline Architecture** inspired by the Chain-of-Responsibility design pattern. 

Every request passes through a registered sequence of independent "Engines". Each engine has a single responsibility (e.g., Validation, Routing, Small Talk, Knowledge Retrieval) and can either modify the context, fulfill the request, or pass it to the next engine.

This chapter explains the execution model, metadata tracing, and how engines are ordered and registered.

---

## 1. Core Concepts

### 1.1 `ConversationContext`
Data enters the pipeline via the `ConversationContext` class. This is a state container that holds:
- `query` (str): The raw user input.
- `session_id` (str): Identifier for retrieving conversation history.
- `metadata` (dict): A shared key-value store where engines deposit intermediate findings (like the normalized query, intents, or detected keywords).
- `intent` (str): The classified purpose of the query.
- `handled` (bool): A critical flag. If set to `True`, pipeline execution halts.

### 1.2 `EngineResult`
When an engine finishes its `process()` method, it returns an `EngineResult` containing:
- `handled` (bool): Whether this engine successfully fulfilled the user's request.
- `reason_code` (str): A developer-readable constant (e.g., `VALIDATION_CHECK_PASSED` or `DECISION_RAG`) explaining what happened.
- `answer` (str): The final text to show the user (if handled).
- `metadata` (dict): Telemetry or debugging data to merge into the context.

### 1.3 `PipelineResult`
When the pipeline finishes (either because an engine handled it, or it exhausted all engines), it returns a `PipelineResult` to the API Router. This contains the final answer and the complete execution trace of every engine that ran.

---

## 2. Pipeline Components

### 2.1 The PipelineRegistry
The `PipelineRegistry` is a singleton that holds the ordered list of active engines.

**Engine Registration & Ordering:**
Engines must execute in a strictly defined order to prevent dependency failures.
1. `ValidationEngine`: Must run first to block attacks.
2. `NormalizationEngine`: Cleans text for downstream regex.
3. `EmptyInputEngine`: Blocks empty strings before they hit expensive logic.
4. `AliasEngine`: Standardizes business acronyms (e.g., WFH -> Work From Home).
5. `QueryDecisionEngine`: Evaluates the normalized text and assigns an Intent.
6. `GreetingEngine`, `GoodbyeEngine`, `ThanksEngine`, `SmallTalkEngine`: Static handlers that check the intent. If matched, they answer and stop execution.
7. `FastPathEngine`: Checks for deterministic business rules. If matched, answers and stops.
8. `KnowledgeEngine`: Evaluates document-aware context.
9. `RAGRetrievalEngine`: The most expensive engine. Only runs if all previous static engines skipped. Executes Vector Search and calls the LLM.
10. `FallbackEngine`: Runs only if RAG fails or no engine handled the request.

### 2.2 The PipelineExecutor
The `PipelineExecutor` iterates through the `PipelineRegistry`.

**Short-Circuit Execution (The `handled` Flag):**
For every engine:
1. It records the `start_time`.
2. It calls `engine.process(context)`.
3. It records the `end_time` and calculates `execution_ms`.
4. It merges the engine's `metadata` into `context.metadata`.
5. It appends the trace to the `routing_audit_log`.
6. **CRITICAL:** If `result.handled == True`, the executor immediately `break`s the loop. No subsequent engines are called. This is how the `GreetingEngine` prevents the `RAGRetrievalEngine` from executing on a simple "Hello".

---

## 3. Code Walkthrough: `app/pipeline/process.py`

### Important Functions

#### `process_query(query, session_id, request_id)`
This is the primary entry point for the backend logic.

**Input:**
- `query`: "What is Mobiloitte's PTO policy?"
- `session_id`: "sess-9876"
- `request_id`: "req-1234"

**Flow:**
1. It initializes `ConversationContext`.
2. It instantiates `PipelineExecutor`.
3. It calls `executor.execute(context)`.
4. It receives the `PipelineResult`.
5. It packages the telemetry trace and returns the final output to the API router.

**Output:**
A structured JSON dictionary containing the answer and exhaustive telemetry.

---

## 4. Telemetry and Execution Metrics

Because AI systems can be non-deterministic and hard to debug, the pipeline architecture relies heavily on telemetry.

Every engine appends a block to the `trace` array.
For example, the trace for a query hitting the `AliasEngine` and then `RAGEngine` looks like this:

```json
"trace": [
  {
    "engine": "Validation",
    "handled": false,
    "executionTimeMs": 0.01
  },
  {
    "engine": "Alias",
    "handled": false,
    "resolved_query": "Work From Home",
    "executionTimeMs": 2.1
  },
  {
    "engine": "RAGRetrieval",
    "handled": true,
    "executionTimeMs": 1205.4,
    "retrievedChunks": [...],
    "embeddingTimeMs": 55.2
  }
]
```
*Why this design was chosen:* This trace is immediately forwarded to the Frontend Developer Mode, allowing engineers and managers to instantly see *exactly* how much time was spent embedding, how much time was spent in the LLM, and why a specific engine made a decision, without ever needing to SSH into a server and read log files.

---

## 5. Alternative Approaches

**Alternative: Monolithic `if/elif/else` block.**
- *Pros:* Slightly faster execution (avoiding class instantiation overhead). Easier for juniors to read initially.
- *Cons:* Impossible to maintain at enterprise scale. Adding a new feature (like a "Profanity Filter") requires modifying the core function, risking breaking the entire application. Testing individual routing steps becomes a nightmare.

**Alternative: LangChain Agents.**
- *Pros:* Out-of-the-box routing using LLMs.
- *Cons:* Extremely slow (adds 2-3 seconds of latency just to figure out what tool to use). Non-deterministic (the LLM might route a greeting to the database). We require strict, sub-millisecond, deterministic routing for enterprise reliability, making LangChain unsuitable for our core pipeline.

---

## 6. Manager Interview Questions

**Q: Why use a Pipeline pattern instead of LangChain Agents?**
*Answer:* LangChain relies on the LLM to make routing decisions (e.g., asking Gemini "Should I use the Database tool or the Greeting tool?"). This adds massive latency and costs, and makes the system non-deterministic. Our Pipeline architecture uses lightning-fast, regex-based Python engines to route queries deterministically in less than 2 milliseconds. The LLM is strictly reserved for generating text at the very end of the pipeline, only when absolutely necessary.

**Q: If we want to add a new feature, like a "Jira Ticket Creator" integration, how hard is that?**
*Answer:* Incredibly easy. Because of the decoupled Pipeline Architecture, we simply create a new `JiraEngine(BaseEngine)`, register it in the `PipelineRegistry` (perhaps right before the `KnowledgeEngine`), and define its intent. We do not need to modify any existing engines or rewrite the core logic.
