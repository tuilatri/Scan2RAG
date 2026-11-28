# API_MAP — Scan2RAG

> Map of every endpoint: method, path, auth, rate limit, response shape.

## Endpoints

| Method | Path | Auth | Rate limit | Description |
|---|---|---|---|---|
| `GET` | `/` | None | None | Root landing info with docs and health URLs |
| `GET` | `/api/v1/health` | None (liveness) | None | Service health check, status, active Milestone 2 features |
| `POST` | `/api/v1/query` | `X-API-Key` / `Bearer` | 60/min per IP | Legal Question Answering with hybrid retrieval, reranking, and citation metadata |
| `POST` | `/api/v1/query/stream` | `X-API-Key` / `Bearer` | 60/min per IP | Real-time SSE streaming endpoint emitting citations, tokens, and done events |
| `POST` | `/api/v1/query/compare` | `X-API-Key` / `Bearer` | 60/min per IP | Additive LangGraph multi-document comparison with bounded evidence retry (max 1) |
| `GET` | `/api/v1/documents` | `X-API-Key` / `Bearer` | 120/min per IP | List canonical legal documents with validity metadata & file sizes |
| `GET` | `/api/v1/documents/{doc_id}` | `X-API-Key` / `Bearer` | 120/min per IP | Get specific document details by ID |
| `GET` | `/api/v1/documents/{doc_id}/pdf` | `?api_key=` (iframe only) | 30/min per IP | Stream raw PDF with HTTP 206 Partial Content (Range bytes) support |
| `GET` | `/api/v1/ocr/tables` | `X-API-Key` / `Bearer` | 120/min per IP | List 111 extracted medical/legal tables with review and VLM status |
| `GET` | `/api/v1/ocr/tables/{node_id}` | `X-API-Key` / `Bearer` | 120/min per IP | Get detailed table matrix, headers, rows, and raw OCR backup |
| `POST` | `/api/v1/ocr/tables/{node_id}/rectify` | `X-API-Key` / `Bearer` | 10/min per IP | Submit human rectification with atomic write & column validation |

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
    "model": "qwen/qwen3.8-27b",
    "complexity": "simple",
    "latency_retrieval_ms": 32.5,
    "latency_rerank_ms": 110.2,
    "latency_total_ms": 840.1
  }
  ```

### `POST /api/v1/query/stream`
- **Request Body:** Same as `QueryRequest`.
- **Response Type:** `text/event-stream` (Server-Sent Events)
- **Event Flow:**
  1. `{"event": "status", "status": "retrieving"}` (emitted immediately, `< 50ms` TTFT)
  2. `{"event": "citations", "citations": [...], "latency_retrieval_ms": 50.2, "latency_rerank_ms": 820.1}`
  3. `{"event": "token", "token": "Căn "}` (emitted token-by-token)
  4. `{"event": "done", "provider": "lm_studio_local", "model": "qwen2.5-1.5b", "latency_total_ms": 11500.0}` (or `{"event": "error", "message": "..."}` on failure)

### `POST /api/v1/query/compare`
- **Request Body (`CompareRequest`):**
  ```json
  {
    "query": "So sánh quy định cận thị giữa Thông tư 105 và Thông tư 106",
    "top_k_retrieval": 15,
    "top_k_rerank": 5,
    "thread_id": "demo-thread-1"
  }
  ```
- `thread_id` tùy chọn, pattern `^[A-Za-z0-9_-]{1,64}$`; chỉ có tác dụng khi `COMPARE_MEMORY=true`.
- **Response Body (`CompareResponse`):** `query`, `answer`, `citations` (same `CitationItem`), `evidence` (`document_id`, `chunk_count`, `citation_ids`), `retry_count` (0 hoặc 1), `provider`, `model`, `verification` (`passed`, `unsupported_numbers`, `checked_numbers`), `version_notes` (`document_id`, `effective_date`, `superseded_by`, `note`), `plan_source` (`llm` / `deterministic`), `sub_queries`, `thread_id`, `history_len`. Số trong `answer` không có trong `citations + query` bị đánh dấu và tạo lại tối đa 1 lần; ngày hiệu lực lấy từ `SemanticLegalChunker.OFFICIAL_EFFECTIVE_DATES`. Planner LLM chỉ chạy khi `PLANNER_LLM=true`; multi-turn chỉ chạy khi `COMPARE_MEMORY=true`.
- **Note:** Endpoint bổ sung dùng LangGraph; `/query` và `/query/stream` vẫn là pipeline rule-based.

### `GET /api/v1/health`
- **Response Body:**
  ```json
  {
    "status": "ok",
    "milestone": "4",
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
- Rate limit storage: in-memory sliding window per client IP (single-instance; use Redis when scaling). Env: `RATE_LIMIT_QUERY_PER_MIN=60`, `RATE_LIMIT_RECTIFY_PER_MIN=10`, `RATE_LIMIT_PDF_PER_MIN=30`.
- Auth scheme: `X-API-Key` or `Authorization: Bearer`. Fail-closed by default; only `GET /api/v1/health` is public. Dev override requires `ENVIRONMENT=development` AND `ALLOW_UNAUTHENTICATED_DEV=true`. PDF iframe may pass `?api_key=` — a browser-visible demo key only, never a production secret. Internal errors are logged server-side and redacted from responses.
