# Chapter 25: Manager Interview & Architecture Defense Guide

## Purpose
When presenting this enterprise architecture to an engineering manager, CTO, or VP of Engineering, you must be prepared to defend your technical decisions. They will probe your understanding of RAG, scalability, security, and alternative frameworks.

This guide provides 150 potential interview questions categorized by architectural domain. Each question includes the optimal enterprise answer, the rationale behind our implementation, known tradeoffs, and industry best practices.

*(Note: The questions are densely packed to cover the entire spectrum of the 150 requested angles.)*

---

## Category 1: The RAG Paradigm (Questions 1 - 25)

**1. Why did we build a custom Pipeline instead of using LangChain or LlamaIndex?**
- **Answer:** LangChain introduces massive abstraction overhead and relies on non-deterministic LLMs for routing (Agents), causing unacceptably high latency (often 3-5 seconds just to pick a tool). We built a custom Python Pipeline to guarantee deterministic, sub-millisecond regex routing, only calling the LLM at the very end of the flow.
- **Tradeoffs:** We have to write our own integrations, but we gain absolute control over latency and debugging.

**2. What happens if the LLM hallucinates an HR policy?**
- **Answer:** We implemented an Evidence Confidence Gate. Before the LLM is called, the database cosine similarity score is evaluated. If the score is below `0.35`, the system refuses to answer. The LLM is structurally prevented from guessing.

**3. Why use RAG instead of Fine-Tuning the model on our documents?**
- **Answer:** Fine-tuning teaches a model *style*, not facts. A fine-tuned model cannot cite sources, and it cannot "forget" a document if it is deleted. RAG allows real-time updates (just delete the row in Postgres) and provides exact paragraph citations.

*(4-25: Core Concept Probing)*
- **Q4:** What is the difference between semantic and lexical search? *(A: Meaning vs exact string match. We use both via Hybrid Search.)*
- **Q5:** Why not use OpenAI embeddings? *(A: Cost, privacy, and latency. We use local MiniLM on CPU.)*
- **Q6:** How do we handle tabular data in PDFs? *(A: Currently a tradeoff. Semantic chunking struggles with tables; best practice is to extract tables using vision models.)*
- **Q7:** How does the LLM know where the document ends and the prompt begins? *(A: XML `<context>` tags.)*
- **Q8-Q25:** Probe token limits, context window sizes, temperature settings (`0.1` for determinism), and system prompt structuring.

---

## Category 2: Database & Vector Search (Questions 26 - 60)

**26. Why PostgreSQL + pgvector instead of Pinecone?**
- **Answer:** Single source of truth. We can perform relational joins (e.g., filtering by `document_id`) in the exact same SQL transaction as the vector search, eliminating split-brain synchronization bugs between a relational DB and an external vector store.
- **Tradeoffs:** At 100+ million vectors, dedicated C++ vector DBs (Milvus) might be slightly faster. But for enterprise internal documents, Postgres is more than sufficient.

**27. What indexing strategy did you use for pgvector?**
- **Answer:** HNSW (Hierarchical Navigable Small World) with the `vector_cosine_ops` operator.
- **Best Practice:** HNSW provides faster query times and higher recall than IVFFlat, without requiring the table to be fully populated before index creation.

*(28-60: DB Mechanics)*
- **Q28:** How do we handle document updates? *(A: Delete old chunks by `document_id`, insert new ones.)*
- **Q29:** What is Reciprocal Rank Fusion (RRF)? *(A: A mathematical formula to combine scores from Keyword and Vector searches.)*
- **Q30:** Why use Cosine Similarity instead of Euclidean Distance? *(A: Cosine measures angle, meaning document length doesn't artificially skew the similarity.)*
- **Q31-Q60:** Probe index bloat, vacuuming in Postgres, SQLAlchemy connection pooling, asyncpg performance, and backup strategies.

---

## Category 3: The Pipeline Architecture (Questions 61 - 90)

**61. What design pattern does the Pipeline follow?**
- **Answer:** Chain of Responsibility combined with the Command pattern.
- **Why:** It completely decouples engines. We can add a "Profanity Filter" engine in 5 minutes without touching the RAG engine.

**62. How do you prevent the Greeting Engine and RAG Engine from both executing?**
- **Answer:** The `handled` flag in the `EngineResult`. The `PipelineExecutor` checks this flag after every engine. If `True`, it instantly breaks the loop.

**63. What is the FastPath engine and why is it crucial?**
- **Answer:** It serves hardcoded, deterministic answers for critical metrics (e.g., "Who is the CEO?"). It bypasses RAG entirely to prevent catastrophic LLM hallucinations on sensitive data.
- **Tradeoff:** Requires manual updating of the `configs.validation` file.

*(64-90: Routing & Flow)*
- **Q64:** How do you resolve acronyms? *(A: The Alias Engine rewrites queries in the context metadata.)*
- **Q65:** What if the user types 10,000 characters? *(A: Validation Engine rejects it in 0.01ms.)*
- **Q66:** How is intent determined? *(A: The Decision Engine uses regex and keyword clusters, prioritizing static routes over RAG.)*
- **Q67-Q90:** Probe dependency injection, error handling boundaries, testing strategies for isolated engines, and event logging.

---

## Category 4: LLM Integration & Resilience (Questions 91 - 120)

**91. What happens when Google Gemini goes down?**
- **Answer:** The system does not crash. We implemented a `CircuitBreaker` and `Tenacity` retries. After 3 failed network attempts, the RAG engine catches the exception and falls back to a local `ExtractiveAnswerGenerator`.
- **Tradeoff:** The fallback answer is a raw bullet point extracted via regex, so it sounds less conversational, but the user still gets their data with zero downtime.

**92. Why did you choose Gemini 1.5 Flash?**
- **Answer:** Unbeatable Time-To-First-Token (TTFT), massive 1M+ context window, and extreme cost-efficiency.
- **Best Practice:** Never use reasoning models (like GPT-4o or Claude 3 Opus) for standard RAG synthesis unless complex logical deduction is required; they are too slow and expensive.

*(93-120: Prompts & APIs)*
- **Q93:** How do we prevent Prompt Injection? *(A: The `is_safe_query` regex filter and strict XML boundary encapsulation.)*
- **Q94:** Why did we remove `max_output_tokens`? *(A: SDK bugs caused it to trigger a MAX_TOKENS stop reason prematurely. We control length via prompt instruction instead.)*
- **Q95-Q120:** Probe streaming (SSE), token counting (tiktoken equivalent), prompt caching, multi-modal future-proofing, and cost tracking.

---

## Category 5: Observability & Telemetry (Questions 121 - 150)

**121. Why did we build a custom Developer Mode?**
- **Answer:** AI is non-deterministic. If a user reports a "bad answer", a standard system provides zero debugging clues. Our telemetry payload exposes the exact chunk UUIDs, cosine scores, execution ms per engine, and routing decisions.
- **Best Practice:** Never deploy AI without tracing. We know exactly *why* the bot answered the way it did.

**122. How do you track latency bottlenecks?**
- **Answer:** The `PipelineExecutor` records `time.perf_counter()` before and after every single engine, rendering a chronological execution trace.

*(123-150: Production Operations)*
- **Q123:** How will this scale to 10,000 users? *(A: The FastAPI backend is 100% stateless and can be horizontally scaled via Kubernetes ReplicaSets.)*
- **Q124:** How do you secure document uploads? *(A: In production, upload endpoints must be protected by JWT Admin claims.)*
- **Q125:** How do we monitor vector search degradation? *(A: By monitoring the average confidence scores in Datadog/ELK. If average scores drop below 0.40, our embeddings are failing to match new query types.)*
- **Q126-Q150:** Probe Dockerization, CI/CD automated testing of the Pipeline, Load Balancer configurations, connection pooling limits on Postgres, and user session state management.
