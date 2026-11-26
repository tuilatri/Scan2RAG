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
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 (frontend):

```bash
cd frontend
npm run dev
```

Xong. Vào `http://localhost:5173`. Kiểm tra API tại `http://localhost:8000/api/v1/health`.

> Lúc này UI chạy được nhưng **chưa trả lời câu hỏi** vì chưa có dữ liệu. Làm mục 2 tiếp.

---

## 2. Chuẩn bị dữ liệu

Clone sạch **không có** PDF và corpus — chúng bị gitignore. Bạn cần PDF gốc, rồi chạy 3 lệnh.

**Bước 1 — Copy PDF vào** `data/raw/` (ví dụ `Thong_tu_105.pdf`, `Thong_tu_88.pdf`).

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

Chạy Qdrant nếu chưa có: `docker compose up -d qdrant`.

Chỉ muốn thử 1 văn bản / vài trang:

```bash
python scripts/ingest_documents.py --file Thong_tu_105.pdf --max-pages 5
```

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

```bash
python scripts/capture_demo_frames.py     # 7 ảnh trong data/exports/demo/frames/
python scripts/build_demo_video.py        # data/exports/demo/scan2rag_demo.mp4
```

Copy video sang chỗ README dùng:

```powershell
Copy-Item data\exports\demo\scan2rag_demo.mp4 docs\assets\scan2rag_demo.mp4 -Force
```

```bash
cp data/exports/demo/scan2rag_demo.mp4 docs/assets/scan2rag_demo.mp4
```

Rồi tạo GIF và kiểm tra:

```bash
python scripts/build_demo_preview_gif.py --build
python scripts/build_demo_preview_gif.py --check
```

Lệnh check phải in `frames=7 transitions=6` và exit `0`.

> `capture_demo_frames.py` cần `playwright` + `pymupdf` (`pip install playwright pymupdf` rồi `python -m playwright install chromium`). Script tự chạy Vite, tự chặn API bằng dữ liệu mẫu.
>
> **Vì sao vùng PDF trong demo có nội dung:** script trả một ảnh trang đã render bằng PyMuPDF thay vì file PDF — Chromium headless không có plugin xem PDF nên cách này hoạt động ổn định. Nếu có `data/raw/*105*.pdf`, script ưu tiên **trang 23 thật** (ảnh scan); nếu không có thì dùng trang mock tự sinh. Caption video vẫn ghi **DEMO DATA** — câu trả lời và điểm số trong chat là dữ liệu mẫu, ngay cả khi trang PDF hiển thị là thật.

---

## 5. Lỗi thường gặp

| Bạn thấy | Nguyên nhân / làm gì |
|---|---|
| `PREFLIGHT — missing data/bm25_index.json` | Chưa chạy mục 2, hoặc đang verify trên máy không có corpus |
| `ModuleNotFoundError: paddle` / `playwright` | Cài lại bằng `backend/requirements.txt`; `pip install playwright pymupdf` cho demo |
| `401 Unauthorized` | Đặt `SCAN2RAG_API_KEY` trong `.env`, `VITE_API_KEY` khớp trong `frontend/.env.local`; dev local cần `ALLOW_UNAUTHENTICATED_DEV=true` |
| Hỏi đáp trả "không tìm thấy" | Chưa nạp Qdrant: chạy lại `ingest_chunks_to_qdrant.py`, kiểm tra `localhost:6333` |
| `CUDA out of memory` | Xem mục 6 |
| `400102 ... image or video format is not supported` trong OpenCode | Do đọc file `.gif` bằng tool `read`; chỉ xem GIF qua ảnh PNG đã export |

---

## 6. Chạy trên máy 4GB VRAM

- Chạy **từng pha**: ingest/OCR/embedding xong mới bật LLM — đừng chạy cùng lúc.
- LM Studio: dùng `Qwen2.5-1.5B` hoặc `3B` dạng `Q4_K_M`, bớt GPU offload.
- Embedding/reranker mặc định chạy CPU (`EMBEDDER_DEVICE=cpu`, `RERANKER_DEVICE=cpu`) để chừa VRAM cho LM Studio.
- Câu hỏi suy luận nặng chuyển sang Groq / OpenRouter / Gemini (điền key trong `.env`).

---

Xem thêm: [README.md](README.md) (kiến trúc, model, benchmark) · [docs/ai-context/README.md](docs/ai-context/README.md).
