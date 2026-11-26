# PROJECT BLUEPRINT & TECHNICAL SPECIFICATION
# VIETNAMESE DOCUMENT INTELLIGENCE (Scan2RAG)

> **Hệ thống AI xử lý, tìm kiếm và hỏi đáp tài liệu scan tiếng Việt (Hybrid Local–Cloud RAG & Agentic Document AI)**  
> *Định hướng Portfolio chuẩn AI Engineer / AI Research Assistant*

---

## 1. TỔNG QUAN DỰ ÁN

### 1.1. Ý tưởng cốt lõi
Dự án tập trung giải quyết bài toán đọc hiểu, xử lý, lưu trữ, tìm kiếm và trả lời câu hỏi dựa trên các văn bản quy phạm pháp luật tại Việt Nam (thử nghiệm ban đầu trên domain: tiêu chuẩn khám sức khỏe và tuyển chọn công dân nhập ngũ).

Điểm khác biệt trọng tâm: Tài liệu đầu vào là **PDF scan từ văn bản giấy** (chất lượng thực tế, có độ nghiêng, nhiễu, con dấu, chữ ký, và bảng phân loại bệnh tật phức tạp), **không phải văn bản digital text có sẵn**.

Hệ thống cung cấp:
- Pipeline tiền xử lý và OCR tài liệu tiếng Việt.
- Cơ chế đánh giá và hiệu chỉnh lỗi OCR (Human-in-the-loop).
- Khôi phục cấu trúc văn bản pháp lý (`Chương -> Điều -> Khoản -> Điểm`).
- Lưu trữ kết hợp: Metadata & Versioning (PostgreSQL — planned) + Vector Embeddings (Qdrant — đã implement).
- Hệ thống Hybrid Retrieval (Dense Vector + BM25) + Reranking.
- Kiến trúc Hybrid Local–Cloud Routing: Dùng model nhỏ chạy local qua **LM Studio** cho câu hỏi đơn giản/tra cứu; gọi Cloud LLM qua các nhà cung cấp miễn phí (**Groq**, **OpenRouter**) cho câu hỏi suy luận phức tạp.
- Tách biệt môi trường cơ sở dữ liệu quan hệ (**PostgreSQL Test & Production** — planned, chỉ có placeholder trong `.env`) ngay từ tầng cấu hình.
- Agentic RAG (LangGraph) hỗ trợ tra cứu đa tài liệu, kiểm tra chứng cứ và hạn chế hallucination.

> **Trạng thái triển khai (cập nhật 2026-11-26):** PostgreSQL và LangGraph ở trên là **thiết kế planned, chưa implement**. Hiện tại metadata/versioning nằm trong file JSON + Qdrant; routing chạy bằng `ModelRouter` dạng rule-based. Nguồn truth: `docs/ai-context/ARCHITECTURE.md`.
- Mọi câu trả lời bắt buộc có **trích dẫn nguồn gốc (Grounded Citations)**: Tên văn bản, số Điều/Khoản, số trang PDF scan.

### 1.2. Hai mục tiêu chiến lược
1. **Mục tiêu 1 — Giải quyết bài toán thực tế**: Tạo trợ lý số tin cậy giúp người dân, công dân tra cứu chính xác quy định về khám sức khỏe và nghĩa vụ quân sự mà không bị phụ thuộc vào thông tin truyền miệng thiếu kiểm chứng.
2. **Mục tiêu 2 — Chứng minh năng lực AI Engineering**: Xây dựng kiến trúc module hóa (pluggable) có khả năng chuyển đổi trực tiếp sang bài toán **Enterprise Document Intelligence / Enterprise RAG** (hợp đồng kinh tế, quy định nội bộ, tài liệu kỹ thuật, SOP).

---

## 2. PHẠM VI DỮ LIỆU & BỘ CORPUS BAN ĐẦU

### 2.1. Danh mục văn bản mục tiêu
| STT | Văn bản | Vai trò & Giá trị pháp lý |
| :---: | :--- | :--- |
| **1** | **Thông tư 105/2023/TT-BQP** | Văn bản gốc quy định tiêu chuẩn sức khỏe và khám sức khỏe nghĩa vụ quân sự |
| **2** | **Thông tư 106/2025/TT-BQP** | Văn bản sửa đổi, bổ sung một số điều của Thông tư 105/2023 |
| **3** | **Văn bản hợp nhất 88/VBHN-BQP** | Bản hợp nhất nội dung sau sửa đổi, thuận tiện cho tra cứu |
| **4** | **Thông tư 68/2025/TT-BQP** | Quy định sửa đổi, bổ sung về tuyển chọn và gọi công dân nhập ngũ |
| **5** | **Hướng dẫn của Cục Quân y** | Hướng dẫn triển khai khám sức khỏe theo từng năm tuyển quân |

> ⚠️ **Nguyên tắc xử lý dữ liệu pháp lý**:
> - Bản hợp nhất (VBHN 88) dùng để tổng hợp tra cứu, nhưng hệ thống vẫn cần lưu văn bản gốc và văn bản sửa đổi để kiểm chứng đối chiếu.
> - Hướng dẫn của Cục Quân y cần xác minh rõ số hiệu và ngày ban hành chính thức trước khi nạp vào corpus.

### 2.2. Đặc tính dữ liệu đầu vào
- Định dạng: PDF scan từ văn bản in, độ phân giải đa dạng (150 - 300 DPI).
- Chứa nhiều bảng phân loại bệnh tật (Phụ lục phân loại thể lực, mắt, tai mũi họng...). Bảng biểu là rủi ro lớn nhất làm gãy cấu trúc văn bản khi OCR.
- Có trang nghiêng (skew), vết đen ở gáy sách, chữ ký và dấu mộc đè lên chữ.

---

## 3. KIẾN TRÚC HỆ THỐNG CHI TIẾT

Hệ thống được tách làm 2 pipeline độc lập:

```text
========================================================================================
                        A. OFFLINE DOCUMENT INGESTION PIPELINE
========================================================================================
[PDF Scan] ──► [PDF Inspector] ──► [Image Preprocessing (OpenCV)] ──► [OCR Engine (PaddleOCR)]
                                                                               │
[Chunking: Structure-Aware] ◄── [Document Structure Parser] ◄── [OCR Quality Validation]
            │                                                                  │
            ├──► [PostgreSQL — planned] (Metadata, Versioning, Pages, Logs)      [Human-in-the-loop]
            └──► [Embedding] ──► [Qdrant Vector DB]

========================================================================================
                        B. ONLINE SERVING & AGENTIC RAG PIPELINE
========================================================================================
[User Query] ──► [Query Analyzer / Router]
                         │
         ┌───────────────┴────────────────────────┐
         ▼                                        ▼
 [Simple / Metadata]                     [Complex / Multi-doc]
         │                                        │
 [Database Lookup / Dense]               [Model Router (hiện tại) / LangGraph — planned]
         │                                        │
         │                              ┌─────────┴─────────┐
         │                              ▼                   ▼
         │                     [Dense (e5/BGE)]      [Sparse (BM25)]
         │                              └─────────┬─────────┘
         │                                        ▼
         │                             [Hybrid Fusion (RRF)]
         │                                        │
         │                                        ▼
         │                               [Cross-Encoder Rerank]
         │                                        │
         │                                        ▼
         │                               [Evidence Checker]
         │                                 /              \
         │                       (Sufficient?)          (Missing?)
         │                           /                      \
         │                         Yes                      Retry Search / Rewrite
         │                         /
         ▼                        ▼
 [Model Router: Local LM Studio (Qwen2.5) vs Free Cloud (Groq / OpenRouter)]
                         │
                         ▼
        [Answer Generation with Grounded Citations]
                         │
                         ▼
              [Citation Verification] ──► [Final Response + UI Page View]
```

---

## 4. CHI TIẾT KỸ THUẬT CÁC MODULE

### 4.1. OCR & Document Preprocessing
- **PyMuPDF**: Trích xuất trang ảnh (render at 300 DPI), kiểm tra có embedded text không.
- **OpenCV Pipeline**:
  - Chuyển xám (Grayscale).
  - Tự động xoay/chỉnh nghiêng (Deskew dựa trên Hough Lines / Minimum Area Bounding Box).
  - Tăng tương phản và khử nhiễu (Bilateral Filter / Adaptive Thresholding).
- **OCR Engine**:
  - `PaddleOCR` (Vietnamese model): Nhận diện chữ tiếng Việt có dấu và tọa độ bounding box.
  - `Tesseract OCR`: Làm baseline so sánh đo lường CER/WER.
  - `Docling`: Nghiên cứu trích xuất bảng biểu (Table structure parsing).
- **Human-in-the-loop Interface**: Cho phép người quản trị đối soát ảnh gốc bên trái, văn bản OCR bên phải, sửa lỗi và lưu phiên bản `approved`.

### 4.2. Document Structure & Chunking
- **Khôi phục phân cấp**: Sử dụng Regex & Rule-based layout parser để bắt các mẫu:
  - `Chương [I|II|...]`: Cấp 1
  - `Điều \d+\.`: Cấp 2
  - `Khoản \d+\.`: Cấp 3
  - `Điểm [a-z]\)`: Cấp 4
- **Chiến lược Chunking**:
  - **Structure-aware**: Mỗi chunk tương ứng với 1 Khoản hoặc 1 Điều nhỏ.
  - **Parent-Child**: Lưu chunk nhỏ (Điểm, Khoản) kèm reference trỏ đến Parent ID (Điều/Chương) để khi retrieval bồi đắp đủ ngữ cảnh cho LLM.

### 4.3. Database & Versioning
- **PostgreSQL (Dual Environment - Test & Production)** — planned, chưa implement:
  - Cấu hình linh hoạt qua biến môi trường: `DATABASE_URL_TEST` (phát triển, chạy automated tests) và `DATABASE_URL_PRODUCTION` (triển khai thực tế).
  - Bảng `documents`: Lưu tên, số hiệu, ngày ban hành, ngày hiệu lực, trạng thái.
  - Bảng `document_relationships`: Quan hệ sửa đổi (thay thế, sửa đổi, bổ sung, hợp nhất).
  - Bảng `document_pages`: Ảnh trang và metadata.
  - Bảng `ocr_results` & `ocr_corrections`: Lưu original text và corrected text để audit.
  - Bảng `conversations` & `messages`: Lịch sử chat.
- **Qdrant**:
  - Collection chứa vector embedding (`multilingual-e5-small` / `BGE-M3`).
  - Payload kèm theo: `document_id`, `article_id`, `clause_id`, `page_number`, `parent_id`, `effective_date`.

### 4.4. Retrieval & Reranking
- **Dense Retrieval**: Cosine similarity trên vector space.
- **Sparse Retrieval**: BM25 trên text tiếng Việt (bóc tách từ bằng `pyvi` hoặc tokenizer chuẩn).
- **Hybrid Fusion**: Sử dụng Reciprocal Rank Fusion (RRF) để kết hợp điểm số.
- **Reranker**: Cross-Encoder nhẹ (multilingual) để sắp xếp lại Top-K chunks trước khi đưa vào context window.

### 4.5. Model Routing & Hybrid Local-Cloud
- **Local Inference (LM Studio)**:
  - LM Studio cung cấp local server tương thích hoàn toàn chuẩn OpenAI API tại `http://localhost:1234/v1`.
  - Dễ dàng tải và nạp các file GGUF quantized nhẹ như `Qwen2.5-1.5B-Instruct` hoặc `Qwen2.5-3B-Instruct` chỉ với vài click trên giao diện trực quan, chủ động tinh chỉnh GPU offload để không tràn 4GB VRAM.
- **Cloud Fallback (Free Providers)**:
  - **Groq API**: Tốc độ cực nhanh (LPU inference), hỗ trợ miễn phí các model mạnh như `llama-3.3-70b-versatile`, `qwen-2.5-32b`.
  - **OpenRouter**: Sử dụng các model gắn tag `:free` (như `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`...).
- **Cơ chế Routing**:
  - Dựa trên độ phức tạp của câu hỏi, số lượng chunks liên quan và loại truy vấn (factual đơn giản -> LM Studio; suy luận so sánh nhiều văn bản -> Groq/OpenRouter).

### 4.6. Agentic Workflow (LangGraph — planned, chưa implement)
- Xử lý các câu hỏi đa bước (Multi-hop), ví dụ: *"Theo Thông tư 106 mới thì quy định về độ cận thị đã thay đổi như thế nào so với Thông tư 105?"*.
- Agent nodes:
  1. `Query Planner`: Bóc tách thành các câu hỏi con.
  2. `Retriever Tool`: Lấy dữ liệu cho từng câu hỏi con từ các thông tư tương ứng.
  3. `Evidence Checker`: Xác nhận đã đủ bằng chứng của cả 2 thông tư chưa.
  4. `Synthesizer`: Tổng hợp câu trả lời so sánh.
  5. `Citation Validator`: Kiểm tra từng nhận định có trỏ đúng điều khoản không.

---

## 5. THIẾT KẾ ĐÁNH GIÁ (EVALUATION & BENCHMARK)

Dự án chú trọng đo lường định lượng thay vì đánh giá cảm tính:

### 5.1. Dataset Ground Truth (50–100 samples)
Bao gồm các nhóm:
- Factual single-hop: Hỏi về 1 quy định cụ thể.
- Multi-document: So sánh giữa 2 thông tư.
- Table-based: Tra cứu chỉ số độ cận, chiều cao, cân nặng trong bảng phụ lục.
- Negative / Out-of-scope: Câu hỏi không nằm trong quy định (hệ thống phải từ chối).

### 5.2. Metrics
- **OCR Quality**: CER (Character Error Rate), WER (Word Error Rate), Table Structure Accuracy.
- **Retrieval Quality**: Recall@K, Precision@K, MRR, nDCG@K.
- **Generation Quality (RAGAS framework)**:
  - `Faithfulness`: Tránh bịa đặt thông tin.
  - `Answer Relevance`: Mức độ trả lời đúng trọng tâm.
  - `Context Precision` & `Context Recall`.
- **System Metrics**: Latency (P50, P95), VRAM usage, API cost ước tính.

---

## 6. PHÂN TÍCH RỦI RO KỸ THUẬT & GIẢI PHÁP ĐỐI ỨNG (GÓC NHÌN PHẦN CỨNG & DỮ LIỆU)

### 6.1. Giới hạn phần cứng (Laptop RTX 3050 Ti 4GB VRAM)
- **Vấn đề**: VRAM 4GB rất dễ bị OOM nếu chạy đồng thời OCR, Embedding và LLM.
- **Giải pháp**:
  - Thiết kế kiến trúc **tách rời hoàn toàn phase Offline (Ingestion) và Online (Serving)**.
  - Khi chạy OCR hoặc Embeddings nạp tài liệu: Không bật LLM.
  - Khi chạy Serving: Chọn model Local LLM nhẹ (1.5B – 3B quantized Q4_K_M) tiêu tốn khoảng ~1.2GB – 2.2GB VRAM.

### 6.2. Bảng biểu khám sức khỏe (Tables) bị vỡ khi OCR
- **Vấn đề**: Bảng phân loại sức khỏe trong Thông tư 105 có nhiều cột (Chỉ số thể lực, điểm 1-6). OCR thông thường dễ gom sai hàng/cột làm đảo lộn kết luận y khoa.
- **Giải pháp**:
  - Dùng module nhận diện layout (Docling hoặc Table Transformer) để parse bảng thành định dạng HTML Table hoặc Markdown Table trước khi chunking.
  - Với các bảng quá phức tạp, tận dụng cơ chế Human-in-the-loop Correction để chuẩn hóa dữ liệu.

### 6.3. Xung đột phiên bản pháp luật (Temporal Consistency)
- **Vấn đề**: Thông tư 106 sửa đổi một số điều của Thông tư 105. Nếu retriever kéo cả 2 điều khoản cũ và mới mà không rõ trạng thái, LLM sẽ trả lời sai quy định hiện hành.
- **Giải pháp**:
  - Ưu tiên retrieval trên **Văn bản hợp nhất (VBHN 88)** cho câu hỏi tra cứu hiện hành.
  - Lưu metadata `superseded: true/false` và `effective_date`. Khi tra cứu thông tư gốc, hệ thống tự kèm ghi chú: *"Điều này đã được sửa đổi bởi Thông tư 106/2025"*.

---

## 7. LỘ TRÌNH TRIỂN KHAI RÚT GỌN (3 MILESTONES THỰC CHIẾN)

### 🎯 Milestone 1: Data Pipeline & Ingestion MVP (Tuần 1 - 2)
- [ ] Thu thập 4-5 file PDF scan chính thức (TT 105, TT 106, VBHN 88, TT 68).
- [ ] Xây dựng script tiền xử lý ảnh với OpenCV (Deskew, Denoise).
- [ ] Tích hợp PaddleOCR bóc tách chữ tiếng Việt; lưu thử nghiệm ra JSON.
- [ ] Viết bộ parser rule-based khôi phục cấu trúc `Chương -> Điều -> Khoản`.
- [ ] Xây dựng giao diện xem và đối soát OCR đơn giản (Human-in-the-loop).

### 🎯 Milestone 2: Core RAG & Benchmark Suite (Tuần 3 - 4)
- [ ] Cài đặt Qdrant và PostgreSQL qua Docker Compose.
- [ ] Nạp vector embeddings với `multilingual-e5-small`.
- [ ] Xây dựng Hybrid Search (Dense + BM25) kèm Reranker.
- [ ] Viết API hoàn chỉnh với FastAPI trả về câu trả lời kèm citation (trang PDF, điều khoản).
- [ ] Tích hợp Local LLM qua **LM Studio** (`Qwen2.5-1.5B`) và Free Cloud LLM (**Groq / OpenRouter**).
- [ ] Xây dựng bộ test 50 câu hỏi ground truth và chạy benchmark với RAGAS.

### 🎯 Milestone 3: Agentic Workflow, Frontend & Portfolio Showcase (Tuần 5 - 6)
- [ ] Xây dựng LangGraph workflow xử lý câu hỏi so sánh đa văn bản.
- [ ] Dựng Web UI React + TypeScript: Cửa sổ Chatbot, Panel hiển thị file scan PDF gốc tương ứng với trích dẫn.
- [ ] Đóng gói Docker Compose, hoàn thiện tài liệu kỹ thuật, bảng số liệu benchmark (`BENCHMARK.md`).
- [ ] Quay video demo 3 phút giải thích bài toán, kiến trúc và kết quả thực nghiệm.

---

## 8. HƯỚNG DẪN MÔ TẢ DỰ ÁN TRONG CV (CV DESCRIPTION)

```text
Vietnamese Document Intelligence — Hybrid Local/Cloud Agentic RAG System
- Built an end-to-end Document AI platform processing scanned Vietnamese legal PDFs (Military Service & Health Regulations) featuring noisy pages, seals, and complex medical classification tables.
- Engineered a document ingestion pipeline using OpenCV for preprocessing (deskew, denoise) and PaddleOCR for Vietnamese text extraction, coupled with a human-in-the-loop correction workflow.
- Implemented structure-aware hierarchical chunking (Chapter-Article-Clause-Point) and hybrid retrieval (Dense + BM25) reranked with cross-encoders in Qdrant.
- Designed a hybrid local/cloud routing architecture: running lightweight quantized models (Qwen2.5 1.5B) locally via LM Studio under 4GB VRAM constraint, falling back to free high-speed Cloud LLMs (Groq, OpenRouter) for complex multi-hop reasoning.
- Designed (planned) an Agentic RAG workflow with LangGraph for cross-statute comparison, temporal versioning resolution, and grounded citation verification down to PDF page numbers. Hiện tại: ModelRouter rule-based + hybrid retrieval + trích dẫn trang PDF.
- Benchmarked OCR (CER/WER) and RAG generation metrics (Faithfulness, Context Recall) using RAGAS across a 50+ ground-truth Q&A dataset.
```
