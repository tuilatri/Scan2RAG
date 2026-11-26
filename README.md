# Vietnamese Document Intelligence (Scan2RAG)

> **Hybrid Local–Cloud RAG & Agentic Document AI for Scanned Vietnamese Documents**  
> *A Production-grade AI Engineering Portfolio Project*

---

## Demo video

<video src="https://raw.githubusercontent.com/tuilatri/Scan2RAG/main/docs/assets/scan2rag_demo.mp4" controls width="100%"></video>

[Tải video demo — 3:00, không âm thanh, caption tiếng Việt](docs/assets/scan2rag_demo.mp4)

Video dùng dữ liệu demo (stub) để đảm bảo tính ổn định khi trình diễn. Các script tạo video nằm tại `scripts/capture_demo_frames.py` và `scripts/build_demo_video.py`.

---

## Tổng quan dự án (Overview)

**Scan2RAG (Vietnamese Document Intelligence)** là hệ thống AI end-to-end xử lý tài liệu chuyên biệt cho văn bản tiếng Việt dạng **PDF scan / ảnh scan** (chất lượng từ scan văn bản giấy, chứa bảng biểu phức tạp, con dấu, chữ ký và độ nhiễu thực tế).

Dự án ban đầu tập trung vào bộ corpus **pháp luật về khám sức khỏe và tuyển chọn công dân nhập ngũ (nghĩa vụ quân sự tại Việt Nam)**, sau đó được thiết kế dạng module hóa có thể mở rộng (pluggable) phục vụ cho hệ thống tri thức nội bộ doanh nghiệp (**Enterprise Document Intelligence & RAG**).

```
               [ Scanned PDF / Image ]
                          │
                          ▼
            [ OCR & Layout Ingestion ] (PaddleOCR, Docling, OpenCV)
                          │
                          ▼
           [ Structure-aware Chunking ] (Chương / Điều / Khoản / Điểm)
                          │
                          ▼
           [ Hybrid Vector Search DB ] (PostgreSQL [Test/Prod] + Qdrant)
                          │
                          ▼
         [ Agentic Query Router & Planner ] (LangGraph / Python)
                   /              \
     (Simple / Fast)            (Complex / Reasoning)
           ▼                              ▼
   [ Local LLM (LM Studio) ]    [ Free Cloud LLM (Groq / OpenRouter) ]
                   \              /
                          ▼
              [ Grounded Citations & Output ]
```

---

## Điểm nổi bật & Kỹ thuật chính (Key Highlights)

1. **OCR & Image Preprocessing Pipeline**: Xử lý nghiêng (deskew), khử nhiễu (denoise), tăng tương phản trước khi nhận diện qua `PaddleOCR` (so sánh baseline với `Tesseract`).
2. **Structure-Aware & Parent-Child Chunking**: Khôi phục cấu trúc văn bản pháp luật Việt Nam (`Chương -> Điều -> Khoản -> Điểm`). Khi match một điểm nhỏ, hệ thống tự động bồi đắp context cha (Khoản, Điều).
3. **Document Versioning & Temporal Consistency**: Quản lý mối quan hệ giữa *Văn bản gốc*, *Văn bản sửa đổi* và *Văn bản hợp nhất* nhằm tránh xung đột điều khoản đã hết hiệu lực.
4. **Hybrid Retrieval + Reranking**: Kết hợp Dense Search (`multilingual-e5-small` / `BGE-M3`) và Sparse Search (`BM25`), sau đó rerank qua Cross-Encoder.
5. **Hybrid Local–Cloud Routing**: Định tuyến câu hỏi: Tra cứu metadata -> Database lookup; Câu hỏi thông thường -> Local LLM (chạy qua **LM Studio**, tối ưu VRAM); Câu hỏi suy luận phức tạp/đa tài liệu -> Cloud LLM miễn phí qua **Groq API** hoặc **OpenRouter** (`:free` models) / Multi-hop Agent.
6. **Rigorous Benchmark & Evaluation**: Đo lường định lượng từ OCR (CER, WER), Retrieval (Recall@K, nDCG) đến Generation (Faithfulness, Answer Relevance qua RAGAS) trên bộ 50-100 ground truth Q&A.

---

## Kiến trúc hệ thống (System Architecture)

### 1. Ingestion Pipeline (Offline)
- **PDF Inspection**: Phân loại file (Digital Text PDF, Scanned PDF, hoặc Hybrid PDF).
- **Preprocessing**: Denoising, Deskewing, Thresholding bằng OpenCV.
- **OCR Engine**: Trích xuất text và layout bounding box bằng PaddleOCR.
- **Human-in-the-loop Correction UI**: Giao diện kiểm tra, so sánh ảnh gốc vs text OCR, lưu vết hiệu chỉnh.
- **Structure Parser & Chunking**: Bóc tách theo cấu trúc phân cấp, sinh metadata chi tiết.
- **Vector & Relational Storage**: Lưu trữ metadata/versioning tại PostgreSQL và embeddings tại Qdrant.

### 2. Query & Serving Pipeline (Online)
- **Query Analyzer & Router**: Phân loại ý định (metadata search, factual single-hop, hay multi-document comparison).
- **Retrieval Engine**: Hybrid search (BM25 + Dense) kết hợp RRF (Reciprocal Rank Fusion) và Reranker.
- **Agentic Workflow (LangGraph)**: Xử lý các câu hỏi phức tạp cần tra cứu nhiều văn bản (so sánh Thông tư 105 và Thông tư 106), đánh giá bằng chứng (Evidence Checker) và retry nếu thiếu thông tin.
- **Citation Validator**: Đảm bảo mọi câu trả lời đều có trích dẫn chính xác đến `Tên văn bản`, `Điều/Khoản` và `Số trang PDF`.

---

## Môi trường & Cấu hình phần cứng mục tiêu

Dự án được tối ưu hóa để chạy và thử nghiệm trên laptop cá nhân có tài nguyên VRAM hạn chế:
- **CPU**: Intel Core i5-12450H (hoặc tương đương)
- **GPU**: NVIDIA GeForce RTX 3050 Ti (4GB VRAM)
- **RAM**: 16 GB
- **Hệ điều hành**: Windows 11 / WSL2 / Linux

> **Chiến lược tối ưu VRAM (4GB)**:
> - Tách biệt pha Ingestion (OCR, Embedding) và Serving (Query, Local LLM) nhằm tránh Out Of Memory (OOM).
> - Ưu tiên model Local LLM quantized nhẹ: `Qwen2.5-1.5B-Instruct` hoặc `Qwen2.5-3B-Instruct` load qua **LM Studio Local Server** (cung cấp endpoint chuẩn OpenAI tại `http://localhost:1234/v1`).
> - Với các tác vụ reasoning nặng: Chuyển tiếp lên **Groq** (siêu tốc, free tier rộng rãi) hoặc **OpenRouter** (sử dụng các model `:free`).

---

## Tech Stack

| Thành phần | Công nghệ lựa chọn | Vai trò |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+, FastAPI | REST API & Core Engine |
| **PDF Processing** | PyMuPDF (fitz) | Đọc, phân tích, render PDF |
| **Image Preprocessing**| OpenCV, Pillow | Deskew, Denoise, Binarization |
| **OCR Engine** | PaddleOCR, Tesseract (baseline) | Nhận diện văn bản tiếng Việt & Layout |
| **Table Extraction** | Docling / Table Transformer | Phân tích bảng biểu tiêu chuẩn sức khỏe |
| **Embeddings** | `multilingual-e5-small`, `BGE-M3` | Sinh vector ngữ nghĩa |
| **Vector Database** | Qdrant | Lưu trữ và tìm kiếm vector |
| **Relational Database**| PostgreSQL (Tách biệt Test & Prod DB) | Lưu metadata, versioning, logs, user |
| **Local LLM** | LM Studio (`http://localhost:1234/v1`) | Chạy suy luận cục bộ bằng Qwen2.5 GGUF |
| **Cloud LLM (Free)**| Groq API, OpenRouter (`:free`) | Suy luận đa tài liệu, reasoning miễn phí |
| **Agent Framework** | LangGraph / LangChain | Workflow có trạng thái, routing, retry |
| **Evaluation** | RAGAS, Custom Evaluation Suite | Đánh giá CER, WER, Recall@K, Faithfulness |
| **Frontend** | React + TypeScript (Vite, Tailwind) | Giao diện Chat, Review OCR, Dashboard |

---

## Cấu trúc thư mục (Project Structure)

```text
Scan2RAG/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── project-blueprint-and-specs.md   # Đặc tả kỹ thuật & Lộ trình chi tiết
│   ├── architecture/                   # Tài liệu thiết kế kiến trúc
│   └── research/                       # Báo cáo benchmark (OCR, Chunking, Retrieval)
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                        # FastAPI routes & dependencies
│   │   ├── core/                       # Config, logging
│   │   ├── ingestion/                  # PDF loader, OCR, preprocessing, parser
│   │   ├── chunking/                   # Structure-aware, parent-child chunkers
│   │   ├── embeddings/                 # Embedding service
│   │   ├── retrieval/                  # Dense, Sparse, Hybrid search & Reranker
│   │   ├── llm/                        # Local & Cloud model clients, Router
│   │   ├── agents/                     # LangGraph workflow, nodes, states
│   │   └── database/                   # PostgreSQL models & Qdrant client
│   └── tests/
├── frontend/                           # React + TypeScript App
├── evaluation/
│   ├── datasets/                       # Question sets & Ground truth
│   ├── ocr/                            # CER/WER scripts
│   ├── retrieval/                      # Recall, MRR, nDCG benchmarks
│   └── reports/                        # Báo cáo kết quả đánh giá
├── data/                               # Dữ liệu cục bộ (ignored in git)
│   ├── raw/                            # PDF scan gốc
│   ├── processed/                      # Text, JSON cấu trúc sau OCR
│   └── exports/
└── scripts/                            # Scripts tiện ích chạy pipeline
```

---

## Lộ trình triển khai rút gọn (Phased Milestones)

- [ ] **Milestone 1 (Data Pipeline & Ingestion MVP)**:
  - Thu thập 4-5 văn bản quy định nghĩa vụ quân sự (TT 105/2023, TT 106/2025, VBHN 88, TT 68/2025).
  - Hoàn thiện script tiền xử lý ảnh và chạy OCR qua PaddleOCR.
  - Xây dựng parser bóc tách cấu trúc Chương - Điều - Khoản.
- [ ] **Milestone 2 (Core RAG & Benchmark Suite)**:
  - Tích hợp Qdrant + `multilingual-e5-small`.
  - Triển khai Hybrid Retrieval (BM25 + Dense) + trích xuất trích dẫn (citations).
  - Tích hợp Free Cloud LLM (Groq / OpenRouter) và Local LLM qua LM Studio (`Qwen2.5-1.5B`).
  - Xây dựng bộ test 50 câu hỏi ground-truth, đo lường các chỉ số với RAGAS.
- [ ] **Milestone 3 (Agentic Workflow, Frontend & Portfolio Showcase)**:
  - Thiết lập LangGraph StateGraph hỗ trợ so sánh văn bản đa nguồn và kiểm tra bằng chứng.
  - Xây dựng Web UI cho phép vừa chat tra cứu, vừa tra cứu chéo trang PDF gốc.
  - Đóng gói Docker, viết tài liệu kỹ thuật hoàn chỉnh và quay video demo 3 phút.

---

## Tài liệu kỹ thuật chi tiết

Chi tiết đầy đủ về toàn bộ kiến trúc, bảng phân tích rủi ro, thông số metric và lộ trình 10 phase được lưu tại:  
 **[Tài liệu Đặc tả Kỹ thuật Toàn diện (Project Blueprint & Specs)](docs/project-blueprint-and-specs.md)**
