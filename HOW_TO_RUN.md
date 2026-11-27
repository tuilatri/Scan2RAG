# HOW_TO_RUN — Scan2RAG

## Bạn muốn làm gì?

| Việc bạn cần | Đọc mục này |
|---|---|
| Lần đầu, cài rồi chạy được giao diện | [1. Cài đặt rồi chạy](#1-cài-đặt-rồi-chạy) |
| Nạp PDF / tạo corpus để hệ thống trả lời được | [2. Chuẩn bị dữ liệu](#2-chuẩn-bị-dữ-liệu) |
| Kiểm tra dự án có lỗi không | [3. Chạy verify](#3-chạy-verify) |
| Tạo lại video GIF demo | [4. Tạo lại demo](#4-tạo-lại-demo) |
| Đang báo lỗi, cần cách sửa | [5. Lỗi thường gặp](#5-lỗi-thường-gặp) |
| Máy yếu / 4GB VRAM | [6. Chạy trên máy 4GB VRAM](#6-chạy-trên-máy-4gb-vram) |

> Lần đầu: làm **mục 1**, sau đó làm **mục 2** để có dữ liệu, rồi **mục 3** để kiểm tra.

---

## 1. Cài đặt rồi chạy

Làm 4 bước này là mở được UI tại `http://localhost:5173`.

**Bước 1 — Tạo file cấu hình** (chạy ở thư mục gốc repo)

```powershell
# Windows
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env.local
```

```bash
# macOS / Linux
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

Mở `.env` và sửa 2 dòng này (các dòng khác giữ nguyên):

```ini
ENVIRONMENT=development
ALLOW_UNAUTHENTICATED_DEV=true
```

Nếu bạn đặt `SCAN2RAG_API_KEY`, thì `VITE_API_KEY` trong `frontend/.env.local` phải **giống hệt**.

Về lựa chọn model: `PREFER_LOCAL=true` (đang bật trong `.env` của bạn) giúp LM Studio được thử **trước cả khi câu hỏi bị xếp `complex`**. Đặt `false` nếu muốn ưu tiên cloud như hành vi mặc định (`.env.example` dùng `false`). Fallback cloud → local → offline vẫn giữ nguyên trong mọi trường hợp.

Planner cho endpoint so sánh: `PLANNER_LLM=false` (mặc định). Đặt `true` nếu muốn LLM chọn văn bản và sinh câu hỏi con — tốn đúng 1 lượt LLM, tự fallback về luật deterministic nếu JSON sai hoặc LLM lỗi.

Multi-turn: `COMPARE_MEMORY=false` (mặc định, stateless). Đặt `true` rồi gửi `thread_id` trong body `/api/v1/query/compare` để hỏi tiếp trong cùng ngữ cảnh. Lịch sử (chỉ câu hỏi + nguồn planner) nằm ở `data/compare_checkpoints.sqlite` (đã gitignore) — đừng commit file này.

**Bước 2 — Cài backend**

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

**Bước 3 — Cài frontend**

```powershell
cd frontend; npm install; cd ..
```

```bash
(cd frontend && npm install)
```

**Bước 4 — Chạy 2 terminal**

Terminal 1 (backend):

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```bash
cd backend
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 (frontend):

```bash
cd frontend
npm run dev
```

Xong. Vào `http://localhost:5173`. Kiểm tra API tại `http://localhost:8000/api/v1/health`.

> Đường dẫn dữ liệu (`data/processed`, `data/bm25_index.json`) đã được resolve từ gốc repo, nên lệnh trên chạy đúng dù bạn `cd backend` hay đứng ở thư mục khác — **không cần `PYTHONPATH`**.

> Lúc này UI chạy được nhưng **chưa trả lời câu hỏi** vì chưa có dữ liệu. Làm mục 2 tiếp.

---

## 2. Chuẩn bị dữ liệu

Clone sạch **không có** PDF và corpus — chúng bị gitignore. Bạn cần PDF gốc, rồi chạy 3 lệnh.

**Bước 1 — Copy PDF vào** `data/raw/` (ví dụ `Thông_tư_105.pdf`, `Thông_tư_88.pdf` — giữ nguyên dấu tiếng Việt).

**Bước 2 — Chạy lần lượt từ thư mục gốc:**

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

| Lệnh | Tạo ra |
|---|---|
| `ingest_documents.py` | `data/processed/*.json` (OCR + cấu trúc Chương/Điều/Khoản/Điểm) |
| `rebuild_bm25_index.py` | `data/bm25_index.json` |
| `ingest_chunks_to_qdrant.py` | Dữ liệu trong Qdrant (cần Qdrant chạy ở `localhost:6333`) |

### Chạy Qdrant server (khuyến nghị)

Nếu chưa có Docker Desktop, bật daemon rồi đợi `docker info` chạy được. Sau đó từ thư mục gốc repo:

```powershell
docker compose up -d qdrant
backend\.venv\Scripts\python.exe scripts\ingest_chunks_to_qdrant.py
backend\.venv\Scripts\python.exe scripts\check_qdrant.py
```

`check_qdrant.py` phải in `points: 7263 (expected 7263)` và `RESULT: PASS`. Khi đó backend dùng Qdrant remote thay vì chế độ local disk DEGRADED. **Không xoá** `data/qdrant_db` — nó vẫn là fallback nếu server tắt.

**Qdrant chạy thế nào:** đây là container Docker riêng, backend **không tự khởi động** nó mà chỉ kết nối `localhost:6333`. Container có chính sách `restart: unless-stopped` → tự chạy lại khi Docker Desktop khởi động. Docker Desktop hiện **không bật auto-start khi đăng nhập Windows**, nên sau khi tắt máy/bật lại bạn cần mở Docker Desktop một lần; container sẽ tự lên.

**Có cần chạy liên tục không:** nên giữ Qdrant chạy trong lúc dùng chatbot để retrieval đầy đủ. Nếu tắt, backend vẫn chạy nhưng fallback sang `data/qdrant_db`: mỗi request chờ ~2s và dữ liệu có thể cũ (log báo DEGRADED). Dữ liệu nằm trong Docker volume `scan2rag_qdrant_storage` nên **không mất** khi tắt container hay tắt Docker — bật lại là có lại 7.263 point.

Muốn tự bật cùng Windows: Docker Desktop → Settings → General → *Start Docker Desktop when you log in*.

Chỉ muốn thử 1 văn bản / vài trang:

```powershell
backend\.venv\Scripts\python.exe scripts\ingest_documents.py --file "Thông_tư_105.pdf" --max-pages 5
```

```bash
backend/.venv/bin/python scripts/ingest_documents.py --file "Thông_tư_105.pdf" --max-pages 5
```

> Tên truyền vào `--file` phải **khớp chính xác** tên file trong `data/raw/`. Xem danh sách bằng `Get-ChildItem data\raw` (Windows) hoặc `ls data/raw`.

---

## 3. Chạy verify

```bash
node scripts/verify.mjs           # đủ 11 gate — chạy trước khi báo "xong"
node scripts/verify.mjs --fast    # nhanh hơn, dùng lúc đang code
node scripts/verify.mjs --only doc-truth
```

| Gate | Cần dữ liệu không | Chạy ở đâu |
|---|---|---|
| `doc-truth`, `backend-lint`, `security-audit`, `frontend-tests`, `test-truth` | Không | CI + máy bạn |
| `corpus-audit`, `score-review`, `vector-audit`, `index-consistency`, `benchmark-truth`, `backend-tests` | **Có** | **Chỉ máy bạn** (đã làm mục 2) |

CI trên GitHub chỉ chạy 5 gate đầu. **CI xanh không có nghĩa là dữ liệu đúng** — phải chạy lệnh 11 gate ở máy bạn.

---

## 4. Tạo lại demo

Cài thêm 2 package cho khâu quay (**chưa có** trong `backend/requirements.txt`):

```powershell
backend\.venv\Scripts\python.exe -m pip install playwright imageio-ffmpeg
backend\.venv\Scripts\python.exe -m playwright install chromium
```

```bash
backend/.venv/bin/python -m pip install playwright imageio-ffmpeg
backend/.venv/bin/python -m playwright install chromium
```

Chạy từ thư mục gốc repo:

```powershell
backend\.venv\Scripts\python.exe scripts\capture_demo_frames.py
backend\.venv\Scripts\python.exe scripts\build_demo_video.py
```

```bash
backend/.venv/bin/python scripts/capture_demo_frames.py
backend/.venv/bin/python scripts/build_demo_video.py
```

Kết quả: 7 ảnh trong `data/exports/demo/frames/` và video `data/exports/demo/scan2rag_demo.mp4`.

Copy video sang chỗ README dùng:

```powershell
Copy-Item data\exports\demo\scan2rag_demo.mp4 docs\assets\scan2rag_demo.mp4 -Force
```

```bash
cp data/exports/demo/scan2rag_demo.mp4 docs/assets/scan2rag_demo.mp4
```

Rồi tạo GIF và kiểm tra:

```powershell
backend\.venv\Scripts\python.exe scripts\build_demo_preview_gif.py --build
backend\.venv\Scripts\python.exe scripts\build_demo_preview_gif.py --check
```

```bash
backend/.venv/bin/python scripts/build_demo_preview_gif.py --build
backend/.venv/bin/python scripts/build_demo_preview_gif.py --check
```

Lệnh check phải in `frames=7 transitions=6` và exit `0`.

> Script tự chạy Vite, tự chặn API bằng dữ liệu mẫu. `pymupdf` và `pillow` đã có trong `requirements.txt`; `playwright` + `imageio-ffmpeg` cần cài riêng như trên.
>
> **Vì sao vùng PDF trong demo có nội dung:** script trả một ảnh trang đã render bằng PyMuPDF thay vì file PDF — Chromium headless không có plugin xem PDF nên cách này hoạt động ổn định. Nếu có `data/raw/*105*.pdf`, script ưu tiên **trang 23 thật** (ảnh scan); nếu không có thì dùng trang mock tự sinh. Caption video vẫn ghi **DEMO DATA** — câu trả lời và điểm số trong chat là dữ liệu mẫu, ngay cả khi trang PDF hiển thị là thật.

---

## 5. Bộ 50 câu nghiệm thu

Bộ 50 câu có đáp án biết trước từ corpus, đo 4 trục: local model, cloud model, Qdrant, LangGraph. Cần Qdrant đang chạy (mục 2) và LM Studio đang bật nếu test local. Từ thư mục gốc repo:

```powershell
backend\.venv\Scripts\python.exe scripts\acceptance_run.py --verify-dataset
backend\.venv\Scripts\python.exe scripts\acceptance_run.py --mode all --limit 3
backend\.venv\Scripts\python.exe scripts\acceptance_run.py --mode all
```

`--mode` nhận `qdrant|local|cloud|langgraph|all`; `--limit N` chạy N câu đầu (`0` = tất cả); `--ids AC-46,AC-48` chạy đúng câu cần kiểm tra; `--out <file>` đổi nơi ghi báo cáo. Mặc định: `data/exports/acceptance_report.json` (gitignored). Script tự spawn uvicorn riêng cho từng mode nên `PREFER_LOCAL` trong `.env` không bị lẫn giữa local/cloud. Nếu đổi wording câu từ chối trong prompt, phải cập nhật `REFUSAL_MARKERS` rồi tính lại metric — answer cũ không đổi, report ghi rõ `regraded_at`. Xem mốc before/after trong `docs/ai-context/ACCEPTANCE_TIMELINE.md`.

Báo cáo gồm: `answer_hit` (đáp án chứa token kỳ vọng, hoặc từ chối đúng với câu ngoài phạm vi), `citation_doc_hit` / `citation_page_hit` (khớp `document_id` / trang PDF), `secondary_cloud_count` (retry sang cloud khác), `local_fallback_count` (fallback LM Studio / offline), `avg_latency_ms`. Riêng LangGraph: `verification_passed`, `with_version_notes`, `with_evidence`. Đây là **đo lường**: script exit 0 dù accuracy thấp; không đưa ngưỡng vào CI (CI không có Qdrant/LLM).

Lưu ý: 50 query trong `data/benchmarks/ragas_milestone2_report.json` bị mojibake, nên bộ này dùng câu tự biên soạn trong `scripts/acceptance_questions.json`.

---

## 6. Lỗi thường gặp

| Bạn thấy | Nguyên nhân / làm gì |
|---|---|
| `PREFLIGHT — missing data/bm25_index.json` | Chưa chạy mục 2, hoặc đang verify trên máy không có corpus |
| `ModuleNotFoundError: paddle` / `playwright` / `imageio_ffmpeg` | Cài lại `backend/requirements.txt`; riêng demo cài thêm `playwright imageio-ffmpeg` vào venv (xem mục 4) |
| `401 Unauthorized` | Đặt `SCAN2RAG_API_KEY` trong `.env`, `VITE_API_KEY` khớp trong `frontend/.env.local`; dev local cần `ALLOW_UNAUTHENTICATED_DEV=true` |
| Hỏi đáp trả "không tìm thấy" | Chưa nạp Qdrant: chạy lại `ingest_chunks_to_qdrant.py`, kiểm tra `localhost:6333` |
| `CUDA out of memory` | Xem mục 6 |
| `400102 ... image or video format is not supported` trong OpenCode | Do đọc file `.gif` bằng tool `read`; chỉ xem GIF qua ảnh PNG đã export |

---

## 7. Chạy trên máy 4GB VRAM

- Chạy **từng pha**: ingest/OCR/embedding xong mới bật LLM — đừng chạy cùng lúc.
- LM Studio: dùng `Qwen2.5-1.5B` hoặc `3B` dạng `Q4_K_M`, bớt GPU offload.
- Embedding/reranker mặc định chạy CPU (`EMBEDDER_DEVICE=cpu`, `RERANKER_DEVICE=cpu`) để chừa VRAM cho LM Studio.
- Câu hỏi suy luận nặng chuyển sang Groq / OpenRouter / Gemini (điền key trong `.env`).

---

Xem thêm: [README.md](README.md) (kiến trúc, model, benchmark) · [docs/ai-context/README.md](docs/ai-context/README.md).
