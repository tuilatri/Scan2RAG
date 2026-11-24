# API_MAP — Scan2RAG

> Map of every endpoint: method, path, auth, rate limit, response shape.

## Endpoints

| Method | Path | Auth | Rate limit | Description |
|---|---|---|---|---|
| `GET` | `/` | None | None | Root landing info with docs and health URLs |
| `GET` | `/api/v1/health` | None | None | Service health check, status, active Milestone 2 features |
| `POST` | `/api/v1/query` | None | None | Legal Question Answering with hybrid retrieval, reranking, and citation metadata |

## Request / Response Schemas

### `POST /api/v1/query`
- **Request Body (`QueryRequest`):**
  ```json
  {
    "query": "Cận thị 3.5 độ có phải đi nghĩa vụ quân sự không?",
    "top_k_retrieval": 15,
    "top_k_rerank": 5,
    "filter_superseded": true
  }
  ```
- **Response Body (`QueryResponse`):**
  ```json
  {
    "query": "Cận thị 3.5 độ có phải đi nghĩa vụ quân sự không?",
    "answer": "...",
    "citations": [
      {
        "id": "thông_tư_88_chunk_1101",
        "document_id": "thông_tư_88",
        "document_name": "Thông tư số 88/VBHN-BQP",
        "breadcrumb": "Thông tư 88 > Phụ lục 1 > Tiêu chuẩn thị lực",
        "page_number": 29,
        "is_table": true,
        "rerank_score": 0.885,
        "snippet": "..."
      }
    ],
    "provider": "groq_cloud",
    "model": "llama-3.3-70b-versatile",
    "complexity": "simple",
    "latency_retrieval_ms": 32.5,
    "latency_rerank_ms": 110.2,
    "latency_total_ms": 840.1
  }
  ```

### `GET /api/v1/health`
- **Response Body:**
  ```json
  {
    "status": "ok",
    "milestone": "2",
    "features": [
      "Dense Vector Search (Qdrant)",
      "Sparse Keyword Search (BM25)",
      "Cross-Encoder Reranker (BGE)",
      "Hybrid Model Router (LM Studio + Groq)",
      "Strict Grounded Citations"
    ]
  }
  ```

## Conventions
- Rate limit storage: None currently (Planned for production gateway)
- Auth scheme: None currently (Open local development API; bearer token planned for Milestone 4)
