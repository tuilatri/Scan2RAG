# KNOWN_TRAPS — Scan2RAG

> Pitfalls already hit — record them so they never repeat. Format: ## N. trap name + explanation + fix.

## 1. 4GB VRAM Out Of Memory (OOM) trap
- **Symptom**: CUDA out of memory error when running OCR, Embeddings, and Local LLM simultaneously.
- **Root cause**: RTX 3050 Ti has only 4GB VRAM. PaddleOCR + BGE-M3 + LLM loaded in memory exceeds capacity.
- **Fix**: Phase execution: run Ingestion (OCR + Embedding) offline; free memory before starting Serving (LM Studio LLM). In LM Studio, restrict local model to Qwen2.5 1.5B/3B quantized Q4_K_M with partial GPU offloading.

## 2. Medical Classification Table structure break in OCR
- **Symptom**: Line-by-line OCR scrambles row-column association in Annexes (Thông tư 105 health criteria tables).
- **Root cause**: Multi-column table layout not preserved by naive horizontal OCR scanning.
- **Fix**: Use layout parsing (Docling / Table Transformer) to convert tables into Markdown/HTML tables before chunking, and utilize human-in-the-loop validation for crucial medical tables. Sau remediation 1B: `scripts/fix_medical_table_columns.py` dời ô điểm sang cột `Điểm` và khôi phục số từ `raw_content_backup` — auditor `shifted_score_cells` giảm **355 → 24**; 24 ca có nhiều điểm trong cùng hàng được ghi `data/exports/score_collision_report.json` để review. Sau 1B-review: 24 quyết định nằm ở `docs/quality/score_collision_decisions.json` (có `reason/reviewer/timestamp`); auditor đếm `reviewed_exceptions=24` và `passed=true` — **ngoại lệ có tên, không nới ngưỡng**. Gate `score-review` trong `kit.config.json` ngăn verify xanh giả.

## 3. Statutory Supersession / Temporal Collision
- **Symptom**: LLM cites obsolete regulations from TT 105 instead of amended rules from TT 106.
- **Root cause**: Naive similarity search retrieves both documents without version context.
- **Fix**: Primary search targets Consolidated Document (VBHN 88); tag chunks with `is_superseded` and `effective_date` metadata.
- **Cập nhật 2026-11-26**: compare graph có node `resolve_versions` — gắn ngày hiệu lực từ `SemanticLegalChunker.OFFICIAL_EFFECTIVE_DATES` (corpus `effective_date` hiện `None` cho mọi node), ghi chú TT105 bị TT106 thay thế và ưu tiên VBHN 88. Chưa sửa corpus/retrieval toàn cục. ⚠️ `document_endpoints.py:31` ghi TT88 = `2023-12-31`, khác chunker (`2024-12-24`) — chưa đối chiếu trong đợt này.

## 4. Toy Test vs Real Corpus Safeguard Trap
- **Symptom**: Safeguard pass 100% in unit tests but lets 7/13 tables lose numbers in production corpus.
- **Root cause**: Mock test used a toy 4-number list `["1", "2", "3", "4"]`. Dropping 1 number is a 25% drop (caught by 10% tolerance). But in real TT 105 tables with 48 numbers, dropping 1-4 numbers is <= 8.3% drop (silently bypassed).
- **Fix**: Zero tolerance number invariant with `collections.Counter(orig) == Counter(rect)` (0% drop, 0% added). Unit tests MUST include realistic fixtures with >=40 numbers, diopters, `%`, and military grades (`1T-6T`).

## 5. Silent Metadata Contract Drift
- **Symptom**: Audit script reports "0 safeguard breaches" even when data has errors, or fails to detect rectified tables.
- **Root cause**: Free-form dictionary keys (`dict.get("key")`) drifted between generator (`vlm_rectified`) and auditor (`rectified_by`), causing silent bypass.
- **Fix**: Enforce Pydantic schema (`TableMetadata`) with typed models and mandatory `corpus-audit` gate inside `kit.config.json`. Sau 1C: BM25 JSON rebuild dùng `LegalChunk.model_dump()` (16 field) và gate `index-consistency` so sánh chunker/BM25/Qdrant (7.259/7.259/7.259), point id `1..N`, 0 breadcrumb `> DOCUMENT`, `superseded_by`/`effective_date` đầy đủ — contract drift bị khóa bằng gate, không phải bằng convention.

## 6. Self-Reported Zero Trap in Auditors
- **Symptom**: `ocr_vision_auditor` báo `shifted_score_cells: 0, score: 100.0, passed: true` dù corpus có hàng trăm ô điểm nằm sai cột; `audit_processed_data.py` bỏ qua number-lock cho bảng HITL nên `thông_tư_105_table_p24` / `thông_tư_88_table_p30` đổi `9 → 5` vẫn in "0 safeguard breaches".
- **Root cause**: Counter khởi tạo rồi không bao giờ tăng; nhánh `hitl_rectified` bị tách khỏi phép đối soát `Counter(orig) == Counter(rect)`; header OCR lỗi (`Diểm` thay vì `Điểm`) làm detector bỏ sót cả bảng.
- **Fix**: Đếm `shifted_score_cells` từ dữ liệu thực (loại cột `STT`, xử lý header mờ), trừ điểm và giữ `passed=false`; áp `check_number_lock(raw_backup, content)` cho mọi bảng đã rectify, kể cả HITL. Không bao giờ nới ngưỡng để gate xanh.
- **Caveat sau 1B-review**: ảnh scan `data/exports/review/thông_tư_88_p30.png` xác nhận dòng "+ Nếu ở 2 bên mắt" có điểm **6** (không phải `9` của backup lẫn `5` của script hardcode). Giá trị đã được re-baseline ở cả `content` và `raw_content_backup` kèm `score_review_*` audit trail → `invalid_score_cells=0`, number-lock vẫn PASS. Không tự đổi số khi chưa có ảnh scan.

## 7. Fail-Open Auth & Internal Error Leak
- **Symptom**: `verify_api_key` trả về sớm khi env key rỗng; 5/8 endpoint business không có dependency auth; exception handler trả `str(e)` cho client; không có rate limit → public API đốt token cloud / tải PDF 57 MB.
- **Root cause**: dev convenience mode được dùng làm mặc định production; CORS từng cho phép `*` kèm credentials; lỗi được serialize trực tiếp từ exception.
- **Fix**: fail-closed (`ENVIRONMENT=production` luôn yêu cầu key; dev override phải `ALLOW_UNAUTHENTICATED_DEV=true`), auth cho mọi route trừ `/health`, `verify_api_key_query` cho iframe PDF, rate limit middleware theo IP, redact lỗi + `logger.exception`. Gate `security-audit` kiểm tra ma trận 8 route, CORS explicit, middleware và fail-closed — không xanh giả (đã sửa lỗi traversal `_IncludedRouter`).

## 8. Benchmark Artifact Tự Nhận PASS
- **Symptom**: `qwen3_vl_4b_report.json` ghi 59/111 và model đơn trong khi corpus có 111/111 (59 Qwen + 52 Gemini); `gemini_auditor_report.json` nhận "1:1 Direct Ground-Truth Cross-Check" dù không script nào sinh; RAGAS ghi `"status":"PASS"` trước assert và tự cộng điểm cho `out_of_scope`; M3 `overall_passed` bỏ qua `citations_under_1s=false`.
- **Root cause**: artifact được viết tay/kế thừa schema cũ; script ghi file trước khi assert; auto-hit làm metric phình; thiếu gate đối chiếu artifact↔corpus↔code.
- **Fix**: script sinh report từ corpus (`check_number_lock`, đếm theo `rectified_model`), Gemini report chỉ nói numeric audit, RAGAS assert trước write + `refusal_hit`, migration giữ measurement cũ nhưng đánh dấu `schema_version:2/migrated_from_legacy`, M3 `overall_passed` tính cả citations latency. Gate `benchmark-truth` check schema/status/metric/count/claim — có negative test chống xanh giả.

## 9. Acceptance Metric Lệch Wording Từ Chối
- **Symptom**: Cloud AC-46/50 báo MISS dù answer đã từ chối ("không chứa...", "không quy định..."); sau khi thêm rule 5 vào prompt, AC-47/48/49 lại MISS vì model dùng câu "nằm ngoài phạm vi...". `doc_hit` từng dùng `all()` nên hiểu allowlist là bắt buộc mọi doc.
- **Root cause**: `REFUSAL_MARKERS` là danh sách cụm cố định, không theo kịp wording của system prompt; phép so sánh allowlist sai thành `all`.
- **Fix**: marker gồm `không chứa`, `không quy định`, `ngoài phạm vi`,...; `doc_hit` dùng `any()`; khi đổi câu từ chối trong prompt phải đổi marker + re-grade report cũ (`regraded_at`). Không dùng marker để cho qua câu có số liệu thật.

## 10. LangGraph Verifier Coi Số Trang Là Hallucination
- **Symptom**: 4/5 câu compare verify FAIL, `unsupported_numbers` gồm `16/18/50/72/74` — toàn số trang trong citation.
- **Root cause**: `evidence_text` chỉ gồm `content` của chunk, thiếu `page_number`/`breadcrumb` mà LLM thực sự thấy trong prompt.
- **Fix**: `verify_answer` đưa metadata chunk vào `evidence_text`; regression test `test_citation_page_number_is_not_flagged_as_unsupported`. Số `6` còn lại của AC-41 là unsupported thật → giữ FAIL, không ép passed.

## 11. Cross-Encoder Đẩy Bảng Điểm Ra Khỏi Top-K
- **Symptom**: `citation_page_hit` 17/22; AC-11/20 có đúng chunk bảng (`is_table=True`, trang 23/29) ở top-15 nhưng bị đẩy khỏi top-5.
- **Root cause**: cross-encoder chấm prose cao hơn bảng đã linearize, dù bảng là nguồn điểm số authority.
- **Fix**: `rerank` cộng `+2.0` cho chunk `is_table` có "điểm" khi query chứa `bảng`/`phụ lục`/`điểm`; subset page 3/8 → 5/8, full 17/22 → 19/22. AC-25/35 vẫn miss vì chunk đúng không nằm top-15 → defer, **không nới expectation trang**.

## 12. Rule Prompt Không Chặn Được Local Model Nhỏ
- **Symptom**: Dù `STRICT_LEGAL_SYSTEM_PROMPT` rule 5 liệt kê rõ "đặt vé máy bay, chỉ số IQ", Qwen2.5-1.5B vẫn bịa quy trình đặt vé và công thức IQ gán cho TT88 (AC-48/49).
- **Root cause**: Model 1.5B không tuân system prompt dài; không có guard deterministic trước khi gọi LLM.
- **Fix**: Giữ rule (cloud tuân và trả đúng câu từ chối), ghi defer cho local; đề xuất guard deterministic hoặc nâng local model. Không đổi expectation để che lỗi.

