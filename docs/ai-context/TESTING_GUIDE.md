# TESTING_GUIDE — Scan2RAG

> **What goes here:** current test counts + exact commands to reproduce them. **How to fill:** run your suites, replace every MEASURE with the measured number, and document one canonical command per suite; `doc-truth.mjs` fails when numbers drift from reality.

## 1. Current test counts (doc-truth parses this table — NEVER guess)

| Metric | Measured Value |
|---|---|
| Collected pytest items | 146 |
| Backend test files | 33 |
| Frontend Vitest items | 32 |
| Frontend test files | 4 |
| Lines in test_vlm_rectifier.py | 59 (non-empty) |

## 2. How to run

### Unit tests
```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q
```

### Verification gates
```bash
node scripts/verify.mjs            # full gate set — use before claiming done
```
`node scripts/verify.mjs --fast` chỉ dùng cho quick iteration: nó lọc gate có tag `slow`, hiện tại không còn gate nào bị lọc; nếu có, lệnh in rõ ID gate bị bỏ qua.

### CI vs local gates

GitHub Actions (`.github/workflows/ci.yml`) chạy 5 gate không cần artifact tạo ở máy local:
`doc-truth`, `backend-lint`, `frontend-tests`, `security-audit`, `test-truth`.

6 gate bị skip trên CI vì cần artifact bị gitignore (`data/raw/*.pdf`, `data/processed/*.json`, `data/bm25_index.json`):

- `corpus-audit`
- `score-review`
- `vector-audit`
- `index-consistency`
- `benchmark-truth`
- `backend-tests` — 101/113 test chạy được, nhưng 12 test đọc PDF/corpus (`test_document_endpoints`, `test_ocr_endpoints`, `test_security`, `test_backend_audit_hardening`, `test_semantic_chunker`) nên chỉ chạy đủ ở local.

Chạy đủ **11 gate** trên máy có artifact — đây là gate bắt buộc trước khi tuyên bố hoàn thành milestone:

```bash
node scripts/verify.mjs
```

CI xanh **không** có nghĩa là corpus/số liệu y tế đã đúng; chỉ lệnh full local ở trên mới kiểm chứng điều đó.

## 3. Test-writing conventions
- Deterministic numerical tests with `collections.Counter`.
- No mock of critical invariants (e.g. 100% number retention in medical tables).

## 4. Acceptance suite (50 câu, không tính vào số test ở mục 1)

Canonical commands:

```bash
backend/.venv/Scripts/python.exe scripts/acceptance_run.py --verify-dataset
backend/.venv/Scripts/python.exe scripts/acceptance_run.py --mode all
```

`scripts/acceptance_questions.json` giữ 50 câu + kỳ vọng (`expected_document_ids`, `expected_pages`, `expected_answer_tokens`, `expect_refusal`). `scripts/acceptance_run.py` spawn uvicorn riêng cho `local` (`PREFER_LOCAL=true`) và `cloud` (`PREFER_LOCAL=false`), gọi SSE `/api/v1/query/stream`, gọi `/api/v1/query/compare` cho 5 câu nhóm `compare`, và chạy `check_qdrant.py`. Kết quả: `data/exports/acceptance_report.json` (gitignored).

Chỉ số: `answer_hit`, `citation_doc_hit`, `citation_page_hit`, `refusal_marker`, `secondary_cloud_count`, `local_fallback_count`, `avg_latency_ms`; LangGraph có `verification_passed`, `with_version_notes`, `with_evidence`. Suite chạy thật với Qdrant/LLM nên **không** nằm trong 5 gate CI. Không được dùng 50 query trong `data/benchmarks/ragas_milestone2_report.json` làm input (bị mojibake).

Dùng `--ids AC-46,AC-48` để chạy lại đúng câu lỗi; mốc before/after và hàng đợi cập nhật tài liệu nằm ở [ACCEPTANCE_TIMELINE.md](ACCEPTANCE_TIMELINE.md).
