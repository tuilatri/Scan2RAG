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

