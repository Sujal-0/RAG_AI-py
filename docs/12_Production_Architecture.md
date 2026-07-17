# Chapter 24: Production Architecture & Scaling

## Purpose
The current architecture runs cleanly on a local machine using Uvicorn and a local PostgreSQL instance. However, to deploy the Mobiloitte AI Knowledge Assistant to an enterprise environment (thousands of employees), the architecture must evolve to handle horizontal scaling, fault tolerance, and security.

This chapter details the deployment strategy, scalability bottlenecks, and observability requirements for production.

---

## 1. Deployment Architecture

### 1.1 Containerization (Docker)
The application must be completely containerized.
- **Backend:** A Dockerfile using a slim Python 3.12 image. It must install `uv`, `torch` (CPU only), and the FastAPI dependencies.
- **Frontend:** A multi-stage Dockerfile. Stage 1 uses Node to `npm run build` the Vite app. Stage 2 uses `nginx:alpine` to serve the static HTML/JS files and proxy `/api/v1` traffic to the backend.
- **Database:** Managed Cloud PostgreSQL (e.g., AWS RDS, Neon, Supabase) with the `pgvector` extension enabled.

### 1.2 Orchestration (Kubernetes / ECS)
To handle traffic spikes, the backend containers should be deployed behind a Load Balancer in a Kubernetes cluster or AWS ECS.
- **Statelessness:** The FastAPI backend is 100% stateless. Sessions are stored in the database. You can spin up 50 backend pods safely.
- **Model Loading:** The only caveat is that `sentence-transformers` loads a 100MB model into RAM on startup. Startup probes must wait for the model to load before routing traffic to the pod.

---

## 2. Scalability Bottlenecks

### Bottleneck 1: Embedding Generation
Embedding documents during ingestion is CPU intensive. 
- **Solution:** In production, Document Ingestion should be decoupled from the main API. When an admin uploads a 500-page PDF, the API should upload the file to S3 and place an event on a message queue (RabbitMQ / AWS SQS). A dedicated fleet of asynchronous Celery workers should pick up the file, chunk it, and embed it, preventing the main API from locking up.

### Bottleneck 2: Database Vector Search
As the database grows past 5 million chunks, exact nearest-neighbor search will slow down.
- **Solution:** Ensure the HNSW index on the `chunks.embedding` column is properly tuned. Increase PostgreSQL `shared_buffers` and `work_mem` to ensure the vector graph stays in RAM.

### Bottleneck 3: Gemini API Rate Limits
Enterprise usage might hit Google's Tokens-Per-Minute (TPM) limits.
- **Solution:** Implement token tracking in `llm_generator.py`. Utilize multiple API keys or a proper enterprise Google Cloud Vertex AI quota. Implement a semantic cache (like Redis) so if two employees ask the same question, the second gets the cached answer without hitting Gemini.

---

## 3. Security

### 3.1 Authentication & Authorization
Currently, Developer Mode and Document Upload are open.
- **Solution:** Implement JWT (JSON Web Token) authentication on the FastAPI router. Add an `@requires_admin` dependency to the `POST /api/v1/documents` route to prevent standard employees from uploading or deleting corporate knowledge.

### 3.2 Secrets Management
API keys must never be hardcoded or checked into Git.
- **Solution:** Use AWS Secrets Manager or HashiCorp Vault to inject the `GEMINI_API_KEY` and `DATABASE_URL` into the container environment variables at runtime.

### 3.3 Rate Limiting
- **Solution:** Implement `slowapi` or an Nginx rate limit to prevent a malicious user from spamming the `/chat` endpoint and draining the LLM budget.

---

## 4. Observability & Logging

Developer Mode telemetry is excellent for the frontend, but we need backend observability for sysadmins.

### 4.1 Centralized Logging
Use standard Python `logging` to output JSON-formatted logs. Aggregate these logs using ELK (Elasticsearch, Logstash, Kibana) or Datadog.

### 4.2 Application Performance Monitoring (APM)
Integrate OpenTelemetry or New Relic into the FastAPI app to track:
- Database query latency (how long did pgvector take?).
- LLM generation time.
- CPU usage of the MiniLM embedding model.

---

## 5. Future Improvements

1. **Streaming Responses:** While the backend supports streaming, the React frontend currently awaits the full JSON payload. Implementing Server-Sent Events (SSE) in the frontend would dramatically improve perceived latency, rendering words as they are generated.
2. **Re-ranking:** Implement a cross-encoder model (e.g., `ms-marco-MiniLM-L-6-v2`) after the hybrid search. The database retrieves the top 20 chunks fast, and the cross-encoder resorts the top 20 with extreme semantic accuracy before sending the top 4 to Gemini.
3. **Multi-Modal RAG:** Allow users to upload charts and images, embed them using CLIP, and use Gemini 1.5 Pro to reason over the images alongside text.
