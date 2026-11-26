# TESTING_GUIDE — Scan2RAG

> **What goes here:** current test counts + exact commands to reproduce them. **How to fill:** run your suites, replace every MEASURE with the measured number, and document one canonical command per suite; `doc-truth.mjs` fails when numbers drift from reality.

## 1. Current test counts (doc-truth parses this table — NEVER guess)

| Metric | Measured Value |
|---|---|
| Collected pytest items | 132 |
| Backend test files | 29 |
| Frontend Vitest items | 31 |
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
