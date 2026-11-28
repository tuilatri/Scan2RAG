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

## Mốc 3 — Sau guard/table retrieval/compare evidence (2026-11-27, chạy lúc 18:28 UTC)

- `generated_at`: `2026-11-27T18:28:50.491121+00:00`
- Lệnh: `scripts/acceptance_run.py --mode all` (report `data/exports/acceptance_report.json`; mốc 2 lưu ở `acceptance_report_m2.json`)

| Trục | answer_hit | citation_doc_hit | citation_page_hit | refusal_marker | avg_latency_ms |
|---|---|---|---|---|---|
| Local | **47/50** | 44/45 | **22/22** | 11/50 | 7.746,1 |
| Cloud | **47/50** | 44/45 | **22/22** | 12/50 | 8.759,0 |
| LangGraph | verification **5/5** | notes 5/5 | evidence 5/5 | — | 20.059,1 |
| Qdrant | PASS · 7.263 points | — | — | — | — |

So với mốc 2: local answer 43→47, page 19→22; cloud answer 45→47, page 19→22; LangGraph 4/5→5/5.
Cloud có `local_fallback_count=16` / `secondary_cloud_count=23` trong lần này — cloud fail nên local nhận thay, đúng thiết kế fallback (ROUTE-1 giữ nguyên theo owner).

## Nhật ký fix mốc 3

| ID | Fix | Kết quả |
|---|---|---|
| ROUTE-1 | **Không đổi router** theo owner | local/simple · cloud/complex · local fallback khi mất mạng |
| DEF-2 | `app/guards/scope_guard.py` + `qa_service` trả SSE refusal sớm | Local 4/4 câu ngoài phạm vi (~5–17ms), in-scope 3/3; unit test 4 passed |
| DEF-3 | top-k 50 + table-node fallback; lọc về trang đầu bảng khi hỏi "trang nào" | AC-25/35 answer 2/2, page 2/2; full page 19/22→22/22 |
| DEF-4 | Compare graph cũng lấy table chunk khi có ý định bảng/điểm | AC-41 `verified=True`; full LangGraph 5/5 |
| DEF-5 | Mốc 3 này + docs cập nhật | — |

## Nhật ký fix (mốc 2)

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
| ROUTE-1 | 6/50 câu cloud do `lm_studio_local` (`router.py:174`) | ✅ **By design theo owner** — local/simple · cloud/complex · local fallback. Không đổi router |
| PAGE-1 | AC-25/35: chunk bảng không nằm top-15 | ✅ Đã sửa mốc 3: top-k 50 + table fallback + lọc trang đầu |
| VERIFY-1 | AC-41: số `6` unsupported | ✅ Đã sửa mốc 3: compare graph lấy table chunk → verified 5/5 |
| LOCAL-1 | AC-48/49 local bịa nội dung ngoài phạm vi | ✅ Đã sửa mốc 3: scope guard deterministic, 5/5 câu ngoài phạm vi |
| METRIC-1 | Cloud answer phụ thuộc marker từ chối | ✅ Ổn định mốc 3; vẫn phải re-grade nếu đổi prompt |
| MODEL-1 | AC-20/29/32 vẫn trượt ở cả local lẫn cloud (3/50) | ⬜ Hạn chế mô hình/grounding — chưa sửa trong mốc này |
| NET-1 | Cloud mốc 3 có 16/50 local fallback do cloud fail | ⬜ Quan sát mạng; hành vi fallback đúng thiết kế |

## Hàng đợi cập nhật tài liệu

- [x] `TESTING_GUIDE.md` §1 — collected pytest items 141 → 142 → **146**; backend files 32 → **33** (thêm `test_scope_guard.py`)
- [x] `TESTING_GUIDE.md` §4 — link tới file timeline này
- [x] `KNOWN_TRAPS.md` — trap 9–12 (mốc 2) + trap 13–15 (mốc 3: detect_documents đệm, compare thiếu bảng, bảng nhiều trang)
- [x] `HOW_TO_RUN.md` mục 5 — cập nhật `--ids` và cách re-grade
- [x] `docs/ai-context/README.md` — thêm dòng index
- [ ] `MODULE_MAP.md` — chỉ cập nhật nếu gate `module-map` báo lệch số dòng sau khi thêm test
- [ ] Sau lần chạy tiếp theo: thêm mốc 3 với số đo mới, đừng xóa mốc 1/2
