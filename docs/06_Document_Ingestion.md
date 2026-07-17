# Chapter 15 - 17: Document Ingestion & Embeddings

## Purpose
An AI Knowledge Assistant is only as smart as the documents it has access to. The Document Ingestion Pipeline is responsible for taking a raw PDF or Word document uploaded by an admin, extracting the text, breaking it into searchable chunks, converting those chunks into vectors, and saving them to the database.

This chapter details exactly how unstructured corporate data is transformed into a highly structured mathematical vector space.

---

## 1. The Ingestion Pipeline

When an admin uploads a document via the frontend, it hits the `POST /api/v1/documents` endpoint. The following pipeline executes synchronously:

### Step 1: Validation
The system checks the MIME type (PDF, DOCX, TXT). It checks the file size. If a file is over 20MB or is an unsupported format, it is rejected with an HTTP 400 error.

### Step 2: Text Extraction
Depending on the file type, a specific extractor is used:
- `PyPDF2` or `pdfplumber` for PDFs.
- `python-docx` for Word documents.
The system strips out images and pure binary data, leaving only raw strings.

### Step 3: Semantic Chunking (`app/chunkers/semantic_chunker.py`)
You cannot embed a 100-page document as a single vector. You must break it down into smaller pieces (chunks). 
- **Why Chunking?** If you embed an entire document, the resulting vector becomes a mathematical average of every concept in the book. It becomes "muddy". If someone searches for "vacation days", the vector for the whole book won't match well. By chunking into paragraphs, each chunk retains a sharp, specific meaning.
- **Why Semantic Chunking?** We don't just split blindly at exactly 500 characters, because that might cut a sentence in half, destroying its meaning. We use regex to split on `\n\n` (paragraph breaks) and `. ` (sentence boundaries).
- **Target Size:** We aim for roughly ~500 characters per chunk, with a small overlap of 50 characters so context isn't lost between boundaries.

### Step 4: Metadata & Heading Extraction
As the chunker reads the document, it looks for lines that resemble headers (e.g., short lines that start with numbers like `1.4 Leave Policy` or are entirely uppercase). 
- **Why Headings?** We attach the detected heading as metadata to every subsequent chunk until a new heading is found. Later, during Hybrid Retrieval, the SQL query applies a massive score multiplier if the user's search term matches the chunk's heading.

### Step 5: Embedding Generation (`app/embeddings/embedding_service.py`)
Each chunk's text is sent to the local `SentenceTransformer` model (`all-MiniLM-L6-v2`).
- The model outputs a list of 384 floating-point numbers.
- Example: `[-0.0142, 0.5512, 0.1198, ...]`

### Step 6: Database Insertion
The original text, the filename, the heading, the page number, and the 384-dimensional vector are all saved into the `chunks` table in PostgreSQL.
The document's status is updated to `READY_FOR_SEARCH`.

---

## 2. The Embedding System (First Principles)

### What is an Embedding?
An embedding is a mathematical translation of a word or sentence into a coordinate in high-dimensional space.
Imagine a 2D graph. The X-axis is "Animals" and the Y-axis is "Vehicles".
- "Dog" is at `[1.0, 0.0]`
- "Car" is at `[0.0, 1.0]`
- "Cat" is at `[0.9, 0.0]`

Notice how "Dog" and "Cat" are physically very close to each other on the graph. This is how the AI knows they are related!
Our model uses 384 dimensions (384 axes) instead of 2. It maps concepts like tone, urgency, subject, verb tense, etc.

### Why use `all-MiniLM-L6-v2`?
- **Speed:** It runs entirely on the CPU in a fraction of a second.
- **Cost:** It is open-source and free. We don't have to pay OpenAI $0.0001 per thousand tokens to embed our massive internal wiki.
- **Dimensionality:** 384 dimensions is small enough that PostgreSQL can search millions of rows rapidly, but large enough to capture rich semantic meaning.

### Cosine Similarity
When a user asks a question, we embed their question into the exact same 384-dimensional space. 
To find the answer, we don't look for matching words. We just look for the chunks that are physically closest to the question's coordinate in the 384D space. 
We use **Cosine Similarity** (the angle between the two vectors) to measure this distance. An angle of 0 degrees means they are identical (score of 1.0).

---

## 3. Manager Interview Questions

**Q: Why don't we just use Keyword Search instead of all this complicated vector math?**
*Answer:* Keyword search relies on exact string matching. If an employee searches for "vacation days", but the HR manual only uses the phrase "Paid Time Off (PTO)", keyword search will return zero results. Vector embeddings understand *meaning*. The vector for "vacation days" is almost mathematically identical to the vector for "Paid Time Off", allowing the system to instantly find the correct paragraph even if the exact words are missing.

**Q: If we have a 500-page PDF, how long does ingestion take?**
*Answer:* Because we use a local, small, CPU-optimized model (MiniLM), we can process roughly 100 pages per second. The bottleneck is usually the PDF text extraction library, not the AI embedding generation.

**Q: What happens if an employee uploads a malicious file with a virus?**
*Answer:* Our ingestion pipeline is completely decoupled from execution. It only extracts strings using safe Python libraries like PyPDF2. It never executes macros or renders HTML, nullifying standard document payloads. Furthermore, validation catches unexpected MIME types and massive files instantly.
