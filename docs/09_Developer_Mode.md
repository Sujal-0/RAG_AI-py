# Chapter 20: Developer Mode Telemetry

## Purpose
AI systems are notoriously difficult to debug because they are often "black boxes" that hide their internal reasoning. When a traditional LLM wrapper returns a wrong answer, it is nearly impossible for an engineer to know *why* without digging through server logs.

The Mobiloitte AI Knowledge Assistant solves this with a built-in **Developer Mode**. Every single query generates a massive payload of routing logic, timing metrics, and mathematical confidence scores. The frontend intercepts this payload and renders a "Debug Trace" panel attached to every message.

This chapter explains every metric shown in the Developer Mode and how to use it to debug the system.

---

## 1. How Telemetry is Gathered

As the `ConversationContext` moves through the `PipelineExecutor`, each engine appends its execution time and specific findings into the `context.metadata` dictionary and the `context.trace` array. 
When the pipeline finishes, the API router packages this raw data into the `debugInfo` object of the JSON response.

Example JSON snippet sent to the frontend:
```json
"debugInfo": {
  "intent": "BUSINESS_RULE",
  "decision": "RAG",
  "confidence": 0.95,
  "executionTimeMs": 1250.4,
  "trace": [...]
}
```

---

## 2. Metrics Breakdown

When you click "Inspect Trace" on a message in the UI, you are presented with several tabs and metrics.

### 2.1 The Execution Timeline (Trace)
This shows the chronological path the query took through the engines.
- **Engine Name:** e.g., `Normalization`, `QueryDecision`, `RAGRetrieval`.
- **Status:** Whether it handled the request (`handled=true`) or passed it along.
- **Latency (ms):** Exactly how many milliseconds that specific engine took. 
  - *Debugging Tip:* If the query is slow, look here. If `QueryDecision` took 5ms but `RAGRetrieval` took 2000ms, you know the LLM or Database is the bottleneck, not the Python routing logic.

### 2.2 Intent & Routing Decisions
- **Detected Topic:** What the Decision Engine thought the user was talking about.
- **Routing Decision:** The path chosen (e.g., `STATIC_ROUTING`, `FAST_PATH`, `RAG`).
- **Why Chosen:** A human-readable string explaining the regex or keyword trigger that caused the routing decision.

### 2.3 RAG Retrieval Metrics
If the query routed to RAG, this section provides deep insight into the vector search.
- **Expanded Query:** Shows what the alias resolver changed the query to before embedding it.
- **Embedding Model:** Shows which model generated the vector (e.g., `sentence-transformers/all-MiniLM-L6-v2`).
- **Embedding Latency:** Time taken by the local CPU to generate the 384D vector.
- **Search Latency:** Time taken by PostgreSQL to execute the complex Hybrid Search SQL query.

### 2.4 Evidence Confidence Metrics
This is the most critical section for debugging "I don't know" answers.
- **Highest Similarity (Cosine Score):** A number between 0.0 and 1.0. 
  - `> 0.60` = Excellent Match
  - `0.45 - 0.60` = Good Match
  - `< 0.35` = Weak Match (Will trigger the Evidence Gate)
- **Confidence Tier:** A string representation of the score (`Excellent`, `Good`, `Weak`).
- **Retrieved Chunks:** A list of the exact paragraphs pulled from the database, including their internal UUIDs, filenames, and individual Reciprocal Rank Fusion (RRF) scores. 
  - *Debugging Tip:* If the bot gives a wrong answer, check the Retrieved Chunks. Did the database pull the wrong paragraph? If yes, the issue is your embeddings. Did it pull the correct paragraph but the bot answered wrong? If yes, the issue is the LLM hallucinating.

### 2.5 LLM / Generation Metrics
- **Prompt Tokens:** How many tokens the context block consumed.
- **Completion Tokens:** How many tokens the Gemini response consumed.
- **LLM Latency:** Time taken by the external API.
- **Fallback Used:** Boolean. If `True`, it means Gemini failed (503/Timeout) and the local Extractive Generator served the response.

---

## 3. Manager Interview Questions

**Q: Our QA team reported that the bot answered a policy question incorrectly. How do we fix it?**
*Answer:* We don't have to guess. We ask QA to click "Inspect Trace" on that exact message and look at the "Retrieved Chunks" metric. 
If the chunks contain the *wrong* policy, it means our Hybrid Search failed to find the right document. We might need to adjust our SQL chunk weighting or add an Alias to `configs.alias`. 
If the chunks contain the *correct* policy, but the bot still answered incorrectly, it means the Gemini LLM failed to read the prompt correctly. We would need to tighten the System Instructions in `llm_generator.py` to stop it from hallucinating.

**Q: A user is complaining the bot takes 4 seconds to answer "Hello". Why?**
*Answer:* That shouldn't happen. By opening the Execution Timeline in Developer Mode, we can see exactly where the time was spent. If the `GreetingEngine` took 4 seconds, there is a severe CPU bottleneck on the server. If the `GreetingEngine` was skipped and the 4 seconds were spent in `RAGRetrieval`, it means our `DecisionEngine` failed to classify "Hello" as a greeting, and routed it to the database by mistake. We would then just add "Hello" to the regex list in `configs.validation`.
