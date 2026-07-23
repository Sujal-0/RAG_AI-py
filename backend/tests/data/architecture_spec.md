# Mobiloitte AI Platform Architecture Spec

## 1. Overview
The Mobiloitte AI Platform is an Enterprise Grade RAG (Retrieval-Augmented Generation) system designed for maximum accuracy, low latency, and zero hallucinations. It comprises several independent but orchestrator-controlled engines:
- Ingestion Engine
- Retrieval Engine
- Generation Engine
- Conversation Intelligence Platform

## 2. Conversation Intelligence Platform
The master controller of the AI platform. It handles session states, conversation planning (via the ConversationPlanner), and orchestrates the Retrieval and Generation engines. It uses the `FinalConversationResponse` DTO to return answers, citations, and metrics.

## 3. Retrieval Engine
The Retrieval Engine uses a 10-stage pipeline:
1. Query Analysis (Normalizes text, detects expectations).
2. Intent Detection (Checks if it's informational, conversational, etc.).
3. Conversation Resolution (Rewrites query based on history).
4. Strategy Selection (Determines dense vs hybrid search).
5. Metadata Filtering (Extracts entities and applies DB filters).
6. Execution (Queries pgvector).
7. Cross-Encoder Reranking (Uses a cross-encoder to rerank top K results).
8. Evidence Gate (Filters chunks below a confidence threshold).
9. Confidence Calculation (Overall score for the retrieval).
10. Result Packaging.

## 4. Generation Engine
The Generation Engine takes the `RetrievalResult` and does:
- Context Compression (Optimizes tokens).
- Extractive Draft (Deterministic extraction).
- Formatting (Applies markdown rules).
- Streaming Response (Yields tokens back to the user).

## 5. Deployment
The platform uses PostgreSQL with the pgvector extension for vector storage. The embedding model is all-MiniLM-L6-v2 which generates 384-dimensional vectors. The LLM used is usually a large provider like Azure OpenAI or Anthropic.
 
 
 
