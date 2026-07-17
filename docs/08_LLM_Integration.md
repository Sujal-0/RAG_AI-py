# Chapter 19: LLM Integration (Gemini)

## Purpose
The entire pipeline exists to gather the precise context needed to formulate an answer. The final step is text synthesis. The system utilizes the **Google Gemini API** (`gemini-1.5-flash`) to read the retrieved database chunks and write a coherent, human-readable response with accurate citations.

This chapter details the `LLMGenerator`, prompt engineering, grounding rules, and resilience patterns (circuit breakers and fallbacks).

---

## 1. Why Gemini 1.5 Flash?

The choice of LLM is critical for a RAG system.
- **Latency:** RAG requires the user to wait for database searches *and* LLM generation. Gemini 1.5 Flash is currently one of the fastest frontier models on the market, minimizing Time-To-First-Token (TTFT).
- **Cost:** Flash models are extremely inexpensive per million tokens compared to "Pro" models, allowing the system to scale to thousands of employees without exorbitant API bills.
- **Context Window:** Gemini 1.5 has an unprecedented 1-million+ token context window, meaning it can easily handle the massive context blocks we retrieve from the database without truncating information.

---

## 2. When is Gemini Called? (And When is it NOT?)

**Gemini is ONLY called if ALL of the following are true:**
1. The user's query did not match a deterministic static intent (like Greetings, Goodbyes, or FastPath business metrics).
2. The Database actually contains uploaded documents.
3. The Hybrid Vector Search successfully found chunks.
4. The chunks passed the **Evidence Confidence Gate** (meaning their cosine similarity score was mathematically high enough to prove relevance).

If *any* of those conditions fail, Gemini is **NOT** called. This strict gating saves massive amounts of money and completely eliminates the chance of the LLM hallucinating an answer to a question it has no context for.

---

## 3. The Prompt Architecture (`app/engines/llm_generator.py`)

When the system decides to call Gemini, it dynamically constructs a prompt.

### 3.1 The Context Block
The retrieved chunks are formatted into an XML-like structure and injected into the prompt.
```xml
<context>
--- Document: HR_Policy.pdf | Section: Travel | Citation: [1] ---
Employees get 20 days PTO.

--- Document: IT_Security.pdf | Section: Passwords | Citation: [2] ---
Passwords must be 12 characters.
</context>
```
*Why this design was chosen:* XML tags (`<context>`) act as hard boundaries. They tell the LLM exactly where the trusted corporate data starts and ends, making it much harder for a user to trick the LLM via prompt injection.

### 3.2 The System Instructions (Grounding & Formatting)
The system prompt enforces absolute obedience to the retrieved context.
```text
You are an Enterprise AI Knowledge Assistant for Mobiloitte.
Your ONLY purpose is to answer employee queries using the provided document context.

# MANDATORY RULES
1. Ground only on retrieved evidence. NEVER hallucinate or guess.
2. If the answer is not fully contained in the context, clearly state: "I couldn't find enough information in the uploaded documents."
3. No metadata leakage. NEVER output UUIDs, chunk IDs, or internal filenames in the body of your response.
4. Keep your tone professional, natural, conversational, and highly readable.
5. Be concise and get straight to the point.
6. Do NOT generate a "Sources" section at the bottom. The system will append the sources automatically.
```
*Note:* We explicitly instruct it to be concise and conversational. We removed strict `max_output_tokens` limits because early testing showed API cut-offs; instead, we rely on the power of instruction-following to keep responses snappy.

---

## 4. Resilience and Fallbacks

External APIs go down. They experience rate limits (429) and high demand (503). An enterprise system cannot crash when Google has an outage.

### 4.1 Tenacity Retries
The API call is wrapped in a `tenacity` `@retry` decorator:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
```
If Gemini returns a `503 Service Unavailable`, the backend pauses for 1 second and tries again. If it fails, it waits 2 seconds, then 4 seconds. 

### 4.2 The Circuit Breaker
If the API fails 3 times consecutively, it throws an exception. Our custom `CircuitBreaker` class detects this and trips OPEN.
While OPEN, the system stops sending requests to Gemini (preventing a flood of doomed API calls) and enters a cooldown period (e.g., 60 seconds).

### 4.3 Extractive Answer Generator (The Safety Net)
When the exception is thrown, the `RAGRetrievalEngine` catches it. Instead of returning a 500 Server Error to the user, it degrades gracefully to the `ExtractiveAnswerGenerator`.
This is a purely local Python class that uses regular expressions to rip the most relevant sentence directly out of the highest-scoring chunk and serves it as a bullet point. 
**The user gets the answer they needed, and they never even realize Gemini was offline.**

---

## 5. Manager Interview Questions

**Q: Can employees trick the LLM into writing Python code or answering trivia questions instead of doing their jobs?**
*Answer:* No. The system prompt commands the LLM: "Your ONLY purpose is to answer employee queries using the provided document context." If they ask for a recipe for cake, the Vector Search will return documents about Software Engineering. The LLM will look at the Software Engineering documents, realize there is no recipe for cake, and respond: "I couldn't find enough information in the uploaded documents."

**Q: What happens if our cloud budget runs out or the Gemini API goes down during a critical demo?**
*Answer:* The demo will not fail. We implemented a robust Extractive Fallback. If the Gemini API becomes unresponsive, the system automatically falls back to a local, regex-based extractive algorithm. It reads the highest scoring paragraph from our database and serves it directly to the user. The response will be slightly more robotic, but 100% accurate and functional.
