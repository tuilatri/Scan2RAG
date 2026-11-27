# ACCEPTANCE_TIMELINE — Bộ 50 câu nghiệm thu

> Mốc so sánh cho những lần chạy sau. Mọi số ở đây copy từ report JSON, không ước lượng.
> Report nằm ở `data/exports/` (gitignore): `acceptance_report_before.json` (run 1), `acceptance_report.json` (run 2, đã re-grade).

## Cách cập nhật

1. Chạy `backend/.venv/Scripts/python.exe scripts/acceptance_run.py --mode all` hoặc `--ids AC-46,AC-48`.
2. Copy `generated_at` + `summary` từ `data/exports/acceptance_report.json` vào mốc mới bên dưới.
3. Nếu đổi marker/prompt mà không gọi lại LLM, ghi rõ `regraded_at` và lý do.
4. Đánh dấu xong task trong `drafts/plans/<...>/task.md` rồi rename `_draft → _done`.

## Mốc 1 — Baseline (2026-11-27)

- Commit: `649773d` trên `eval/acceptance-50`
- `generated_at`: `2026-11-27T16:29:27.396974+00:00`
- Lệnh: `scripts/acceptance_run.py --mode all` (50 câu × local/cloud + 5 câu LangGraph + Qdrant)

| Trục | answer_hit | citation_doc_hit | citation_page_hit | refusal_marker | avg_latency_ms |
|---|---|---|---|---|---|
| Local | 42/50 | 39/45 | 17/22 | 5/50 | 7.476,1 |
| Cloud | 42/50 | 39/45 | 17/22 | 13/50 | 9.365,1 |
| LangGraph | verification 1/5 | notes 5/5 | evidence 5/5 | — | 38.086,9 |
| Qdrant | PASS · 7.263 points | — | — | — | — |

## Mốc 2 — Sau các fix (2026-11-27, re-grade 17:51 UTC)

- `generated_at`: `2026-11-27T17:32:33.795775+00:00`
- `regraded_at`: `2026-11-27T17:51:17.311477+00:00` — chỉ tính lại metric sau khi bổ sung marker `ngoài phạm vi`; **answer không đổi**.

| Trục | answer_hit | citation_doc_hit | citation_page_hit | refusal_marker | avg_latency_ms |
|---|---|---|---|---|---|
| Local | **43/50** | **44/45** | **19/22** | 7/50 | 7.281,7 |
| Cloud | **45/50** | **44/45** | **19/22** | 16/50 | 9.956,1 |
| LangGraph | verification **4/5** | notes 5/5 | evidence 5/5 | — | 20.549,8 |
| Qdrant | PASS · 7.263 points | — | — | — | — |

## Nhật ký fix

| ID | Phát hiện | Nhãn | Kết quả |
|---|---|---|---|
| FIX-1 | Marker từ chối lệch wording; `doc_hit` dùng `all()` | harness bug | Cloud refusal 0/2 → 2/2; doc allowlist 0/2 → 2/2 (AC-31/40) |
| FIX-2 | Verifier thiếu metadata trang | system bug | Subset 0/4 → 3/4; full 1/5 → 4/5; AC-41 còn số `6` unsupported thật |
| FIX-3 | Local 1.5B bỏ qua rule out-of-scope | model limit | Prompt rule đã thêm; cloud tuân, local AC-48/49 vẫn hallucinate → defer |
| FIX-4 | Cross-encoder đẩy bảng điểm khỏi top-5 | system bug | Boost `is_table` có "điểm"; subset page 3/8 → 5/8; full 17/22 → 19/22; AC-25/35 defer |
| FIX-5 | Chưa có mốc so sánh cho tài liệu | docs | File này + index trong `docs/ai-context/README.md` |

## Các phát hiện chờ xử lý

| ID | Vấn đề | Trạng thái |
|---|---|---|
| ROUTE-1 | 6/50 câu cloud vẫn do `lm_studio_local` trả lời (`router.py:174`: simple → local dù `PREFER_LOCAL=false`) | ⬜ Chờ owner quyết định có đổi routing không |
| PAGE-1 | AC-25/35: chunk bảng đúng không nằm trong top-15 retrieval | ⬜ Defer — cần mở rộng retrieval, không nới expectation trang |
| VERIFY-1 | AC-41: số `6` trong answer không có trong evidence | ⬜ Giữ FAIL; chỉ sửa nếu evidence thực sự thiếu chunk |
| LOCAL-1 | AC-48/49 local vẫn bịa nội dung ngoài phạm vi | ⬜ Defer — cần guard deterministic hoặc model lớn hơn |
| METRIC-1 | Cloud answer 45/50 phụ thuộc marker từ chối; phải re-grade nếu đổi prompt | ⬜ Kiểm tra lại ở lần chạy sau |

## Hàng đợi cập nhật tài liệu

- [x] `TESTING_GUIDE.md` §1 — collected pytest items 141 → 142 (thêm regression test)
- [x] `TESTING_GUIDE.md` §4 — link tới file timeline này
- [x] `KNOWN_TRAPS.md` — trap 9–12 (metric từ chối, verifier page number, rerank bảng, local model nhỏ)
- [x] `HOW_TO_RUN.md` mục 5 — cập nhật `--ids` và cách re-grade
- [x] `docs/ai-context/README.md` — thêm dòng index
- [ ] `MODULE_MAP.md` — chỉ cập nhật nếu gate `module-map` báo lệch số dòng sau khi thêm test
- [ ] Sau lần chạy tiếp theo: thêm mốc 3 với số đo mới, đừng xóa mốc 1/2
