# HARD CONSTRAINTS & AGENT LINTING ROADMAP
# (Triết lý Lauren Tan / @poteto — Hard Constraints over Soft Prompts)

> **Tài liệu tham chiếu & Kế hoạch triển khai linter/gate cho Scan2RAG**  
> *Mục tiêu: Ngăn chặn triệt để AI Slop và ép Agent tuân thủ kỷ luật kỹ thuật bằng các công cụ tất định (Deterministic Guards), không dựa vào lời nhắc văn bản đơn thuần.*

---

## 1. TRIẾT LÝ CỐT LÕI (THE LAUREN TAN METHODOLOGY)

Trong quá trình làm việc với Coding Agent (Claude, Cursor, Copilot, Gemini), các lời dặn trong file markdown (`AGENTS.md`, `CLAUDE.md`) chỉ là **"Soft Prompts"** — LLM rất dễ quên hoặc lách luật khi ngữ cảnh (context window) dài ra.

> **"Soft Prompts Lose. Hard Constraints Win."**  
> Bất kỳ sai sót nào AI thường xuyên mắc phải, thay vì viết thêm một dòng cảnh báo vào file `.md`, hãy chuyển hóa nó thành **một Linter Rule, Type Check, hoặc Gate Runner trả về Exit Code $\ne 0$**.

---

## 2. KẾ HOẠCH TRIỂN KHAI THEO TỪNG GIAI ĐOẠN

Khi dự án bước vào giai đoạn code thực tế, ta sẽ kích hoạt lần lượt các Hard Constraints sau:

### 2.1. Backend (Python / FastAPI) — Kích hoạt tại Milestone 1
Khi bắt đầu viết code cho `backend/app/`:

1. **Cài đặt Ruff (Linter & Formatter siêu tốc)**:
   ```bash
   pip install ruff
   ```
2. **Cấu hình `ruff.toml` hoặc `pyproject.toml`**:
   - `E`, `F`: Bắt lỗi syntax, unused imports, biến chưa định nghĩa.
   - `I`: Bắt buộc sắp xếp import ngăn nắp.
   - `B`: Bugbear (các lỗi thiết kế code phổ biến trong Python).
   - `UP`: Tự động nâng cấp cú pháp Python hiện đại (Python 3.10+).
   - **Cấm print bừa bãi**: Yêu cầu dùng module `logging` chuẩn, không cho phép Agent để lại `print()` debug tràn lan.
3. **Thêm Gate vào `kit.config.json`**:
   ```json
   {
     "id": "backend-lint",
     "cmd": "ruff",
     "args": ["check", "app/"],
     "cwd": "backend",
     "tags": ["lint", "backend"],
     "optional": false
   }
   ```

---

### 2.2. Frontend (React / TypeScript) — Kích hoạt tại Milestone 3
Khi bắt đầu dựng giao diện `frontend/src/`:

1. **Strict TypeScript (`tsc --noEmit`)**:
   - Bật `noImplicitAny: true`, `strict: true` trong `tsconfig.json`.
   - **Tác dụng**: Cấm tiệt Agent dùng kiểu `any` để qua mặt compiler; buộc Agent phải định nghĩa rõ ràng data schema của PDF, Chunk và Citation.
2. **ESLint Anti-Slop Rules**:
   - Chặn lạm dụng `useEffect` không cần thiết.
   - Cấm inline styles bừa bãi; ép dùng Tailwind tokens nhất quán.
3. **Thêm Gate vào `kit.config.json`**:
   ```json
   {
     "id": "frontend-typecheck",
     "cmd": "npx",
     "args": ["tsc", "--noEmit"],
     "cwd": "frontend",
     "tags": ["types", "frontend"],
     "optional": false
   }
   ```

---

### 2.3. Architectural Constraints (Kiến trúc & Ranh giới Module)
Tránh việc Agent import lung tung làm phá vỡ phân tầng hệ thống:

1. **Quy tắc ranh giới (Boundaries)**:
   - Tầng `retrieval/` và `llm/` **không bao giờ** được import trực tiếp code của `frontend/`.
   - Code `api/` không được bypass tầng Service để gọi trực tiếp các câu lệnh SQL thô không kiểm soát.
   - Khi cần siết chặt, sử dụng công cụ kiểm tra kiến trúc như `import-linter` (đã từng dùng hiệu quả bên Amazon Clone).

---

## 3. CHECKLIST KHI KÍCH HOẠT HARD CONSTRAINTS

Mỗi khi thêm một Linter mới:
- [ ] Thêm câu lệnh chạy vào danh sách `gates` trong `kit.config.json`.
- [ ] Chạy thử `node scripts/verify.mjs` để xác nhận gate hoạt động chính xác.
- [ ] Nếu Agent vi phạm, `verify.mjs` phải báo **FAIL (Exit code 1)** và chặn kết thúc task cho đến khi Agent tự sửa xanh toàn bộ.
- [ ] Không biến linter thành rào cản quá khắt khe ở những ngày đầu prototype; chỉ bật strict mode khi khung sườn module đã thành hình.
