# Chapter 14: RAG Deep Dive

## Purpose
This is the most complex and important engine in the entire Mobiloitte AI Knowledge Assistant. 
The **Retrieval-Augmented Generation (RAG)** engine is responsible for finding accurate information across thousands of uploaded enterprise documents and generating a human-readable, cited response.

This chapter breaks down RAG from first principles, explains exactly how our custom implementation works, and details the rigorous gating mechanisms that prevent AI hallucinations.

---

## 1. What is RAG? (First Principles)

### Why RAG?
Large Language Models (LLMs) like ChatGPT or Gemini are trained on the public internet. If you ask an LLM, "What is the Mobiloitte Travel Policy?", it has no idea, because your corporate HR documents are private. It will either guess (hallucinate) or refuse to answer.

**Retrieval-Augmented Generation (RAG)** solves this by doing exactly what a human does when reading a book:
1. **Retrieve:** Search a database to find paragraphs relevant to the user's question.
2. **Augment:** Paste those paragraphs into the LLM's prompt.
3. **Generate:** Ask the LLM to read the pasted paragraphs and answer the question using *only* that text.

### Embeddings vs. LLMs
An **Embedding Model** (like SentenceTransformers MiniLM) is a small, specialized AI that converts words into lists of numbers (vectors) based on their meaning. It cannot generate text.
An **LLM** (like Gemini) is a massive AI that generates text. 
We use the small Embedding Model locally to search the database, and the massive LLM remotely to generate the final answer.

### Semantic Search vs. Lexical Search
- **Lexical Search (Keyword Search):** Looks for exact word matches (e.g., SQL `LIKE '%travel%'`). If the document says "flight rules", keyword search fails to find it.
- **Semantic Search (Vector Search):** Looks for meaning. It knows that "travel" and "flight rules" are conceptually identical.

---

## 2. Our Implementation: The Pipeline

When a query reaches `app/engines/rag_engine.py`, the following sequence executes:

### Step 1: Query Expansion
User query: `"deployment metrics"`
The system optionally runs query expansion to append synonyms or resolve acronyms, yielding: `"deployment metrics software releases live projects"`. This broadens the search net.

### Step 2: Embedding Generation
The expanded query is sent to `app/embeddings/embedding_service.py`. The local MiniLM model converts the string into a 384-dimensional vector array: `[-0.014, 0.552, 0.119, ...]`.

### Step 3: Hybrid Retrieval (The Magic)
We query the PostgreSQL `chunks` table. A standard vector search just looks for meaning, which is bad for exact part numbers or names. We solve this using **Hybrid Retrieval**, executing three searches simultaneously in one SQL query:
1. **Vector Search:** `ORDER BY vector <=> query_vector` (Finds semantic meaning).
2. **Keyword Search:** `WHERE text ILIKE '%deployment%'` (Finds exact words).
3. **Metadata Search:** `WHERE heading ILIKE '%metrics%'` (Weights chunks higher if the word appears in the document heading).

### Step 4: Reciprocal Rank Fusion (RRF)
The database returns three different lists of chunks. We must merge them.
We use an algorithm called **RRF**. If Chunk A was #1 in Vector Search, and #5 in Keyword Search, it gets a combined score. This ensures that chunks containing *both* the semantic meaning and the exact keywords rise to the absolute top.

### Step 5: Evidence Confidence Gate
This is our primary anti-hallucination defense.
We evaluate the highest scoring chunk from the RRF ranking.
- If the score is `> 0.60`, we categorize it as `Excellent` evidence.
- If the score is `< 0.35`, the evidence is too weak. The Evidence Gate SLAMS SHUT. 
- The system short-circuits, completely bypassing Gemini, and returns: *"I couldn't find enough information in the uploaded documents."*

### Step 6: Deduplication & Context Building
If the gate opens, the top 4 chunks are selected. We deduplicate them (removing overlapping text) and format them into an XML-like block:
```xml
<context>
--- Document: HR_Policy.pdf | Section: Travel | Citation: [1] ---
Employees get 20 days PTO.
</context>
```

### Step 7: Gemini Generation
The context block and the user's query are sent to the Gemini API (`app/engines/llm_generator.py`).
The System Prompt strictly enforces:
- "Ground only on retrieved evidence."
- "Be concise and get straight to the point."
- "Seamlessly integrate facts into your prose."

### Step 8: Source Citations & Telemetry
When Gemini returns the string, we append the exact filenames and page numbers to the bottom as a `**Sources:**` footer. We record exactly how many milliseconds the embedding, searching, and generating took, and return the `PipelineResult`.

---

## 3. Extractive Fallback

What happens if the Gemini API is down, experiencing high demand (503), or your API key expires?
Instead of crashing, the `RAGRetrievalEngine` catches the network exception. It degrades gracefully to the **Extractive Answer Generator**. 
Instead of sending the chunks to an LLM, the backend uses a local Python regex script to extract the single most relevant sentence from the top chunk and serves it as a bullet point. 
The user still gets their answer, and the system never goes offline.

---

## 4. Manager Interview Questions

**Q: Why don't we just use ChatGPT to read our documents?**
*Answer:* Security and scale. Uploading sensitive Mobiloitte documents directly to public ChatGPT breaches data privacy. Furthermore, LLMs cannot "store" thousands of documents in memory. Our RAG architecture stores the documents securely in our own PostgreSQL database. We use math (vectors) to extract only the 3 most relevant paragraphs, and we send *only those 3 paragraphs* to the LLM to format the answer.

**Q: Why use Hybrid Search instead of just Vector Search?**
*Answer:* Vector search understands concepts, but it fails at exact keyword matching. If a user asks for "Error Code 4B-99X", a pure vector search will fail to find it because "4B-99X" doesn't have a semantic "meaning" in English. Keyword search finds it instantly. By fusing Vector + Keyword + Metadata (Hybrid Search), we get the best of all worlds: we can find concepts, exact part numbers, and heavily weight sections based on their document headings.

**Q: How do you guarantee the AI won't hallucinate and give a user incorrect policy information?**
*Answer:* Two methods. First, the **Evidence Confidence Gate**. Before we even wake up the LLM, we check the mathematical cosine distance of our search results. If the database doesn't have a highly confident match, we refuse to answer. The LLM is never given the opportunity to guess. Second, through strict prompt engineering, the LLM is commanded to act only as a summarizer of the provided XML context, not as a general knowledge bot.
