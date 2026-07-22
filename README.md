# Enterprise AI Document Assistant

A full-stack, secure, multi-tenant web application that enables employees to upload internal documents (PDF, Word docs, spreadsheets, text files) and ask natural-language questions with real-time streaming answers and precise source citations.

---

## 🏗️ Architecture Overview

```
                      +-----------------------------+
                      |     Next.js 14 Frontend     |
                      | (App Router, Tailwind, UI)  |
                      +--------------+--------------+
                                     | REST / SSE (Streaming Chat)
                                     v
                      +-----------------------------+
                      |       FastAPI Backend       |
                      +----+-------------------+----+
                           |                   |
            Auth / Metadata|                   | Background Jobs
                           v                   v
                +------------------+   +------------------+
                | PostgreSQL (DB)  |   |  Celery + Redis  |
                |  Multi-tenant    |   |  Worker Ingest   |
                +------------------+   +--------+---------+
                                                |
                                    Extract/Chunk/Embed
                                                v
                                       +------------------+
                                       | Vector Store     |
                                       | (ChromaDB)       |
                                       +--------+---------+
                                                | Top-k Chunks
                                                v
                                       +------------------+
                                       |  Claude API RAG  |
                                       | (Stream + Cite)  |
                                       +------------------+
```

---

## 🚀 Key Features

### 1. Security & Multi-Tenancy
- **Row-Level Tenant Isolation**: Every DB query and vector search filter is strictly scoped by `org_id`.
- **Role-Based Access Control (RBAC)**: Supports `ADMIN`, `MANAGER`, and `EMPLOYEE` roles with document access restrictions (`PUBLIC`, `MANAGERS_ONLY`, `ADMIN_ONLY`).
- **Audit Logging**: Full audit trail tracking logins, file uploads, document deletions, user creations, and RAG queries.

### 2. Hand-Rolled RAG Pipeline
- **Document Parsing**: Parses PDFs (`pypdf`), Word documents (`python-docx`), spreadsheets (`openpyxl`), and plaintext.
- **Overlapping Semantic Chunking**: Chunks text into ~400 token windows with a 50 token overlap while preserving exact page number metadata.
- **Vector Storage**: Persists embeddings in ChromaDB with metadata filtering.
- **Streaming & Citations**: Real-time SSE response streaming via Anthropic Claude SDK with clickable citation modals showing document title, page #, and snippet preview.

### 3. Modern Glassmorphic UI
- Built with **Next.js 14 (App Router)**, **TypeScript**, **Tailwind CSS**, **Zustand**, and **React Query**.
- Interactive file drag-and-drop, real-time ingestion status badges (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), and admin analytics metrics dashboard.

---

## 🛠️ Quickstart with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/yourorg/enterprise-ai-doc-assistant.git
   cd enterprise-ai-doc-assistant
   ```

2. Configure environment variables in `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your `ANTHROPIC_API_KEY` (and optional `OPENAI_API_KEY`).

3. Launch all services:
   ```bash
   docker-compose up --build
   ```

4. Access the web app:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Tests

Run pytest for backend authentication, document chunking, and RAG pipeline prompt assembly:
```bash
docker-compose exec backend pytest tests
```
Or locally inside `backend/`:
```bash
pytest tests
```

---

## 💡 Technical Design Decisions (Interview Talking Points)

- **Why RAG instead of fine-tuning?**  
  Fine-tuning is expensive, static, and leaks internal data across boundaries. RAG provides real-time access to uploaded documents, strict multi-tenant access filtering by `org_id` and role permissions, and verifiable source citations without retrain latency.

- **How multi-tenancy is enforced:**  
  Multi-tenancy is enforced in depth:
  1. JWT claims contain `org_id` and `role`.
  2. FastAPI dependencies extract and enforce `org_id` on every SQL query (`select(Document).where(Document.org_id == current_user.org_id)`).
  3. ChromaDB vector queries include a mandatory `{"org_id": {"$eq": user_org_id}}` filter.

- **Chunking strategy:**  
  Fixed character window (~1600 characters ~= 400 tokens) with 200 character overlap, preserving page boundaries. This ensures semantic context continuity across page boundaries while maintaining accurate page citation tags.
