# TESTING_GUIDE — Scan2RAG

> **What goes here:** current test counts + exact commands to reproduce them. **How to fill:** run your suites, replace every MEASURE with the measured number, and document one canonical command per suite; `doc-truth.mjs` fails when numbers drift from reality.

## 1. Current test counts (doc-truth parses this table — NEVER guess)

| Metric | Measured Value |
|---|---|
| Collected pytest items | 79 |
| Backend test files | 20 |
| Frontend Vitest items | 21 |
| Frontend test files | 4 |
| Lines in test_vlm_rectifier.py | 59 (non-empty) |

## 2. How to run

### Unit tests
```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q
```

### Fast verification gate
```bash
node scripts/verify.mjs --fast
```

## 3. Test-writing conventions
- Deterministic numerical tests with `collections.Counter`.
- No mock of critical invariants (e.g. 100% number retention in medical tables).
