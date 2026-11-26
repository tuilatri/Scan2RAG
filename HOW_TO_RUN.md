# HOW_TO_RUN — Scan2RAG

Hướng dẫn chạy Scan2RAG từ một clone sạch. Đọc [README.md](README.md) để biết kiến trúc, model và benchmark.

> **Điều kiện tiên quyết quan trọng:** các artifact dữ liệu (`data/raw/*.pdf`, `data/processed/*.json`, `data/bm25_index.json`, `data/qdrant_db`) bị gitignore. Clone sạch **không có** chúng — phải có PDF gốc và chạy pipeline ở mục 3 để hệ thống trả lời được câu hỏi.

---

## 1. Yêu cầu

| Thành phần | Khuyến nghị | Ghi chú |
|---|---|---|
| Python | 3.10+ (đã test 3.11/3.12) | Dùng venv riêng trong `backend/.venv` |
| Node | 22 (đúng bản CI) | `npm` đi kèm |
| Qdrant | `localhost:6333` | `docker compose up -d qdrant` hoặc cài local |
| LM Studio | `http://localhost:1234/v1` | **Tùy chọn** — chỉ cần cho LLM local |
| GPU CUDA | RTX 3050 Ti 4GB (hoặc CPU) | `paddlepaddle-gpu==3.3.1` trong `requirements.txt` cần CUDA; dùng `requirements-ci.txt` nếu chỉ cần chạy gate CPU |
| Docker | Tùy chọn | Chỉ cần nếu dùng Qdrant qua compose |

Máy 4GB VRAM: **không** chạy OCR + Embedding + LLM cùng lúc. Xem mục 6.

---

## 2. Cài đặt

### 2.1. Cấu hình môi trường

```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env.local
```

```bash
# macOS / Linux
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

Các biến cần chỉnh trước khi chạy:

| Biến | Ý nghĩa |
|---|---|
| `ENVIRONMENT` | `development` hoặc `production`. Ở production luôn yêu cầu API key (fail-closed). |
| `SCAN2RAG_API_KEY` | Key bảo vệ API. `ALLOW_UNAUTHENTICATED_DEV=true` **chỉ** dùng khi dev local. |
| `VITE_API_KEY` (frontend) | Phải khớp `SCAN2RAG_API_KEY` để iframe PDF và các request được authorize. |
| `VITE_API_BASE_URL` | Mặc định `http://localhost:8000`. |
| `GROQ_API_KEY` / `OPENROUTER_API_KEY` / `GEMINI_API_KEY` | Chỉ cần nếu dùng cloud LLM. |
| `LOCAL_LLM_MODEL` | Tên model đã load trong LM Studio, mặc định `qwen2.5-1.5b-instruct`. |
| `QDRANT_HOST` / `QDRANT_PORT` | Mặc định `localhost:6333`. |

> Không commit `.env` hay `frontend/.env.local`. Xem `.env.example` cho danh sách đầy đủ (embedding, reranker, rate limit, Langfuse).

### 2.2. Backend

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

> Chỉ cần chạy gate kiểm tra (không cần OCR GPU)? Dùng `backend/requirements-ci.txt` — bản CPU, đã loại `paddlepaddle-gpu`/CUDA.

### 2.3. Frontend

```powershell
cd frontend
npm install
cd ..
```

```bash
(cd frontend && npm install)
```

---

## 3. Sinh artifact dữ liệu (bắt buộc để trả lời được)

Đặt PDF gốc vào `data/raw/` (ví dụ `Thong_tu_105.pdf`, `Thong_tu_88.pdf`), rồi chạy lần lượt từ **root repo**:

```powershell
backend\.venv\Scripts\python.exe scripts\ingest_documents.py --all --skip-existing
backend\.venv\Scripts\python.exe scripts\rebuild_bm25_index.py
backend\.venv\Scripts\python.exe scripts\ingest_chunks_to_qdrant.py
```

```bash
backend/.venv/bin/python scripts/ingest_documents.py --all --skip-existing
backend/.venv/bin/python scripts/rebuild_bm25_index.py
backend/.venv/bin/python scripts/ingest_chunks_to_qdrant.py
```

| Script | Kết quả |
|---|---|
| `ingest_documents.py --all` | `data/processed/<tên_văn_bản>.json` (OCR, bảng, cấu trúc Chương/Điều/Khoản/Điểm) |
| `rebuild_bm25_index.py` | `data/bm25_index.json` (~8 MB) từ corpus đã xử lý |
| `ingest_chunks_to_qdrant.py` | Nạp chunk vào collection `vietnamese_legal_docs` (cần Qdrant đang chạy) |

`ingest_documents.py` nhận `--file <tên.pdf>` để xử lý một file, `--max-pages N` để giới hạn số trang (hữu ích khi thử nghiệm).

> Nếu thiếu corpus, các gate `corpus-audit`, `score-review`, `benchmark-truth`, `index-consistency`, `backend-tests` sẽ fail hoặc báo số bằng 0 — đây là nguyên nhân lỗi PREFLIGHT từng gặp trên CI.

---

## 4. Chạy ứng dụng

Terminal 1 — backend:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```powershell
cd frontend
npm run dev
```

```bash
cd frontend
npm run dev
```

- API health: `http://localhost:8000/api/v1/health`
- UI: `http://localhost:5173`
- Nếu dùng Docker: `docker compose up -d qdrant backend frontend` (compose cũng định nghĩa `postgres`, nhưng lớp PostgreSQL hiện **chưa được implement** trong app).

---

## 5. Chạy verify

```bash
node scripts/verify.mjs          # FULL 11 gate — bắt buộc trước milestone
node scripts/verify.mjs --fast   # Quick iteration (hiện không lọc gate nào)
node scripts/verify.mjs --only doc-truth
```

| Gate | Cần artifact không | Chạy ở đâu |
|---|---|---|
| `doc-truth`, `backend-lint`, `security-audit`, `frontend-tests`, `test-truth` | Không | CI + local |
| `corpus-audit`, `score-review`, `vector-audit`, `index-consistency`, `benchmark-truth`, `backend-tests` | **Có** (PDF/corpus/BM25/Qdrant) | **Chỉ local** |

CI trên GitHub chỉ chạy 5 gate đầu (xem `.github/workflows/ci.yml`). **CI xanh không có nghĩa là dữ liệu đúng** — xem `docs/ai-context/TESTING_GUIDE.md` §2.

---

## 6. Tối ưu VRAM 4GB

- Chạy **hai pha riêng**: Ingestion (OCR + Embedding) xong mới đến Serving (query + LLM).
- Model local: `Qwen2.5-1.5B/3B` dạng GGUF `Q4_K_M` trong LM Studio, GPU offload một phần.
- Reranker/Embedder mặc định chạy CPU (`EMBEDDER_DEVICE`, `RERANKER_DEVICE`); câu hỏi reasoning nặng chuyển sang Groq/OpenRouter/Gemini.

---

## 7. Tạo lại demo (GIF/MP4)

```powershell
backend\.venv\Scripts\python.exe -m pip install playwright
backend\.venv\Scripts\python.exe -m playwright install chromium
backend\.venv\Scripts\python.exe scripts\capture_demo_frames.py
backend\.venv\Scripts\python.exe scripts\build_demo_video.py
python scripts\build_demo_preview_gif.py --build
python scripts\build_demo_preview_gif.py --check
```

`capture_demo_frames.py` tự chạy Vite, chặn API bằng dữ liệu stub và xuất 7 PNG tĩnh sang `data/exports/demo/frames/`. `build_demo_video.py` ghép thành MP4 (7 cảnh, ~3 phút, không âm thanh, có caption). `build_demo_preview_gif.py` lấy 7 mốc trong MP4 để ra GIF 7 frame cho README.

### Vì sao vùng xem PDF trong demo bị trắng?

Không phải lỗi sản phẩm. script quay dùng `mock_page.pdf` **1 trang, 1,4 KB** do chính nó sinh ra (PDF gốc ~78 MB bị gitignore), rồi nhúng qua `<iframe src="...pdf#page=...">`. Chromium **headless** của Playwright không có plugin PDF viewer nên iframe tải được file nhưng không vẽ. Toolbar/breadcrumb/trích dẫn vẫn hiện vì đến từ dữ liệu stub. Trình duyệt thường (có PDF viewer) với file PDF thật sẽ hiển thị bình thường.

---

## 8. Sự cố thường gặp

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| `PREFLIGHT — missing data/bm25_index.json` | Chưa chạy mục 3, hoặc đang chạy verify trên máy không có artifact |
| `ModuleNotFoundError: paddle` khi chạy test | Cài `backend/requirements.txt` (đầy đủ), không dùng `requirements-ci.txt` cho backend-tests |
| `401 Unauthorized` | Đặt `SCAN2RAG_API_KEY` trong `.env` và `VITE_API_KEY` khớp trong `frontend/.env.local`; dev local có thể `ALLOW_UNAUTHENTICATED_DEV=true` |
| Trả lời "không tìm thấy" dù đã ingest | Kiểm tra Qdrant `localhost:6333` và chạy lại `ingest_chunks_to_qdrant.py` |
| OOM CUDA | Tách pha Ingestion/Serving, giảm model local về 1.5B Q4_K_M |
| `node scripts/verify.mjs` fail ở `test-truth` trên Linux | Đã sửa: script tự chọn `.venv/bin/python` trên POSIX; cập nhật code mới từ `main` |
