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

## Mốc 4 — Version metadata trong prompt chat (2026-11-28)

- Phạm vi: **verification có chọn lọc**, không phải full 50.
- Môi trường: Qdrant **UP** (`check_qdrant.py` PASS · 7.263 points, Docker Desktop + container tự bật lại sau reboot); **LM Studio DOWN** (không tìm thấy executable) → `--mode local` thực chất fallback Groq. Vì vậy mốc 3 vẫn là số full gần nhất cho local model.
- Lệnh:
  ```
  backend\.venv\Scripts\python.exe scripts\acceptance_run.py --mode local --ids AC-01,AC-02,AC-03,AC-29
  backend\.venv\Scripts\python.exe scripts\acceptance_run.py --mode cloud --ids AC-29
  ```

| Kiểm tra | Kết quả |
|---|---|
| AC-29 local | **OK** — "TT105 đã bị thay thế bởi TT106, không còn là văn bản hiện hành" |
| AC-29 cloud | **OK** — cùng nội dung |
| AC-01/02/03 | 3/3 OK, citation doc 4/4, page 3/3 |
| Unit test `test_prompt_marks_superseded_document` | PASS |

`build_qa_prompt` có impact **HIGH** sau reindex (7 symbols / 4 processes) nên **không đụng**; metadata được nối trong `qa_service._append_version_notes` thay thế (impact LOW). `TESTING_GUIDE` §1: 146 → **147** pytest items.

## Mốc 5 — Full 50 với LM Studio thật (2026-11-28)

- `generated_at`: `2026-11-28T05:50:30.150407+00:00`
- Môi trường: Qdrant **UP** 7.263; **LM Studio UP** (`qwen2.5-1.5b-instruct` ELOADED, port 1234) → số local thật, không phải Groq fallback.
- Report mốc 3 lưu ở `data/exports/acceptance_report_m3.json`.

| Trục | answer_hit | citation_doc_hit | citation_page_hit | refusal_marker | avg_latency_ms |
|---|---|---|---|---|---|
| Local (LM Studio thật) | **44/50** | 44/45 | **22/22** | 11/50 | 7.147,2 |
| Cloud | **47/50** | 44/45 | **22/22** | 19/50 | 11.097,1 |
| LangGraph | verification **4/5** | notes 5/5 | evidence 5/5 | — | 36.155,1 |
| Qdrant | PASS · 7.263 points | — | — | — | — |

So với mốc 3 (cũng full, local 47/50 · cloud 47/50 · LG 5/5): page/doc giữ nguyên; local answer giảm 3, LangGraph giảm 1 — do **biến động model**, không phải thay đổi code giữa 2 lần chạy.

- Local misses: AC-20, **AC-22, AC-29**, AC-32, AC-33, AC-35. AC-29 dù pass ở mốc 4 (Groq) vẫn trượt với Qwen 1.5B → block hiệu lực có tác dụng với cloud, **chưa đủ với local nhỏ**. Không đổi expectation.
- Cloud misses: AC-04, AC-32, AC-33.
- LangGraph: AC-42 `unsupported_numbers={'106'}` (lần trước pass) — biến động sinh số, giữ FAIL thật.
- Cloud `local_fallback_count=0`; 6/50 vẫn do `lm_studio_local` vì câu simple → local theo routing đã duyệt.

## Mốc 6 — Truth + Corpus Graph + eligibility chain (2026-11-28)

- `generated_at`: `2026-11-28T11:41:31.605657+00:00`
- Dataset **52 câu** (thêm AC-51/52 từ 2 ảnh thực tế). Report mốc 5 lưu ở `data/exports/acceptance_report_m5.json`.
- Qdrant **7266 points** (3 rule node mới từ PDF text layer, `scripts/rebuild_critical_rules.py`).

| Trục | answer_hit | citation_doc_hit | citation_page_hit | avg_latency_ms |
|---|---|---|---|---|
| Local | **47/52** | 46/47 | **24/24** | 7.439,9 |
| Cloud | **45/52** | 46/47 | **24/24** | 8.038,7 |
| LangGraph | **5/5** | notes 5/5 | evidence 5/5 | 26.796,2 |
| Qdrant | PASS · 7.266 points | — | — | — |

**AC-51** (viễn thị): local + cloud đều OK, citation có trang **2** (rule "Không gọi nhập ngũ... viễn thị các mức độ") và trang **4** (không cho điểm). **AC-52** (loạn thị): OK, citation có trang **23** (2/3 điểm) và trang **1** (loại 1–3).

Thay đổi kiến trúc (impact CRITICAL/HIGH của `chunk_document`/`_has_table_intent` đã báo owner nên **không đụng**):
- `scripts/rebuild_critical_rules.py` + 3 point mới; rule trọn câu, không còn fragment 2–3 dòng.
- `backend/app/graph/corpus_graph.py` + `scripts/legal_rule_edges.json`: edge typed, resolve anchor → chunk.
- `qa_service`: method `_has_eligibility_intent`/`_graph_candidates` **mới**, không sửa intent cũ.
- `backend/app/grounding/claim_verifier.py`: check claim trong chat path.
- Dataset đánh dấu `weak:true` cho **33 expectation cũ** (token chung) — 47/52 không còn được hiểu là accuracy người dùng.

Các phát hiện mới: `score_collision_decisions.json` có 24 entry, **reviewer=agent**, 19/24 evidence=`raw_backup_match` — không phải HITL thật. Chi tiết trong KNOWN_TRAP 17–18.

## Layer A pilot — Canonical facts (2026-11-28)

- Không chạy acceptance mới; đây là nền input cho graph, chưa thay đổi hành vi chatbot.
- `scripts/build_canonical_facts.py`: render TT105 p23 + TT88 p29 + Hướng dẫn p1/p2/p4 ở 200 DPI vào `data/exports/review/canonical/`.
- `data/canonical/medical_scores.json`: **30 fact + 3 rule**; tất cả `needs_human:true`, `authoritative:false`.
- `scripts/audit_canonical_facts.py` (gate local, CI skip): PASS với 33/33 chưa có human sign-off — tức là **chưa được phép dùng làm nguồn quyết định**.
- Chỉ là pilot 2 trang bảng + 3 rule; không phải "trích xuất tuyệt đối 111 bảng / 287 trang".
- Gates: `verify --fast` 12/12, doc-truth 1/1.

## Layer A2 — Full extraction + review workflow (2026-11-28, v0.5.0)

- `scripts/build_canonical_facts.py` quét **111/111 bảng**, render 114 ảnh evidence 200 DPI, parse **88 bảng có dòng điểm** → **1.163 fact + 3 rule**.
- `scripts/review_canonical_fact.py`: CLI duyệt của người; `reviewer:"agent"` bị từ chối khi `--approved`; bắt `--evidence-checked`.
- `audit_canonical_facts.py`: authoritative chỉ hợp lệ nếu có decision người thật + evidence checked. Hiện **1.166/1.166 entry vẫn `needs_human:true`, 0 authoritative**.
- Không đổi hành vi chatbot; chưa chạy acceptance mới. Đây là nền cho graph/decision engine (đợt B2/C2).
- Gates: `verify --fast` 12/12, doc-truth 1/1.

## DOCX ingestion + inspired OCR layers (2026-11-28)

- Nguồn: `drafts/outsource/ocr-result.docx` do **VietNamOCR 3.3.1** tạo (Google ScreenAI + SLANet/Paddle ONNX + ProtonX v1.4-NC). Attribution: [`../THIRD_PARTY_ATTRIBUTION.md`](../THIRD_PARTY_ATTRIBUTION.md). **Không copy binary/model vào repo.**
- `scripts/ingest_docx_facts.py`: đọc lưới ô DOCX, chọn cột `Điểm` theo header, map 13 bảng vào doc/page → **678 fact** (`source_kind:"docx"`).
- 3 lớp inspiration open: `table_structure.py` (header-aware), `vietnamese_corrector.py` (từ điển deterministic), `ocr_pipeline.py` (adapter engine-swappable). Không nhân bản ProtonX/ScreenAI.
- `build_canonical_facts.py` dùng `table_structure` → bỏ dòng header: fact giảm **1163 → 884**, bảng có điểm **88 → 48**.
- `audit_canonical_facts.py` đọc cả 2 store: **884 + 678 = 1562 fact + 3 rule**, tất cả `needs_human:true`, 0 authoritative.
- Không đổi hành vi chatbot; chưa chạy acceptance mới.

## OCR Benchmark Phase 0 (2026-11-28)

- `scripts/benchmark_ocr_engines.py` chạy được; report: `data/benchmarks/ocr_engine_comparison.json` (`provisional_reference:true`).
- **Đã sửa lỗi live OCR**: pre-import `torch` trước `paddleocr` để tránh `shm.dll [WinError 127]`; `--live` chạy được (PaddleOCR 3.7 / PP-OCRv6, GPU). Cũng sửa placeholder `__NUM1__`↔`__NUM10__` trong `vietnamese_corrector` và thêm hint header `Đim`.
- **Corpus mode (baseline cũ)**: 38 ref fact, 13 khớp, 8 đúng → accuracy `0.2105`, number retention `0.1385`, protected 3/3. Đây là khoảng cách giữa **dữ liệu đang dùng** và DOCX.
- **Live mode (sau sửa)**: 77 ref fact (đã đổi TT88 sang p31 có reference), **0 khớp**, accuracy `0.0`, protected **0/3**. Nguyên nhân nhìn trực tiếp từ preview: PaddleOCR mất dấu (`Bnh tt`, `Đim`, `Phu luc I`) và để điểm ở dòng riêng nên `TableExtractor` không đổ được vào cột `Điểm`.
- Đọc thẳng: đây là bằng chứng OCR hiện tại **chưa tương đương** bản Word — đúng mục đích Giai đoạn 0. Không đổi corpus/serving; chưa re-ingest.

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
| MODEL-1 | Mốc 5: local miss AC-20/22/29/32/33/35; cloud miss AC-04/32/33 | ⬜ Hạn chế mô hình/grounding — không nới expectation |
| LOCAL-VAR-1 | AC-29 pass với Groq (mốc 4) nhưng vẫn miss với Qwen 1.5B (mốc 5) | ⬜ Cần guard chắc hơn cho local nhỏ nếu muốn 50/50 |
| LG-VAR-1 | AC-42 unsupported `106` ở mốc 5 (mốc 3/4 pass) | ⬜ Biến động sinh số; giữ FAIL thật, không ép passed |
| NET-1 | Cloud mốc 3 có 16/50 local fallback; mốc 5 về 0 | ✅ Không còn dấu hiệu bất thường ở mốc 5 |

## Hàng đợi cập nhật tài liệu

- [x] `TESTING_GUIDE.md` §1 — collected pytest items 141 → 142 → 146 → **147**; backend files 32 → **33**
- [x] `TESTING_GUIDE.md` §4 — link tới file timeline này
- [x] `KNOWN_TRAPS.md` — trap 9–12 (mốc 2) + 13–15 (mốc 3) + **16** (mốc 4: payload `superseded_by` rỗng)
- [x] `HOW_TO_RUN.md` mục 5 — cập nhật `--ids` và cách re-grade
- [x] `docs/ai-context/README.md` — thêm dòng index
- [x] `MODULE_MAP.md` — bổ sung `guards/`, `services/qa_service.py`, `retrieval/` với số dòng đo được (P0 mốc 5)
- [ ] Sau lần chạy tiếp theo: thêm mốc 3 với số đo mới, đừng xóa mốc 1/2
