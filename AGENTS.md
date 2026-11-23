<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Scan2RAG** (258 symbols, 337 relationships, 5 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Scan2RAG/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Scan2RAG/clusters` | All functional areas |
| `gitnexus://repo/Scan2RAG/processes` | All execution flows |
| `gitnexus://repo/Scan2RAG/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

# Behavioral Guidelines (Karpathy)

Bản đầy đủ: `docs/ai-context/BEHAVIORAL_GUIDELINES.md` — 4 rule bắt buộc mỗi session:
**Think Before Coding · Simplicity First · Surgical Changes · Goal-Driven Execution**.
Tinh thần: hành vi tối giản, sửa đúng chỗ không đụng adjacent code, mỗi task có tiêu chí kiểm chứng được. Đọc file đó khi bắt đầu session.

---

# Pre-Task Workflow (adapted from `.agent/rules/AUTO_AGENT_LOADING.md`)

## Pre-Task Checklist

At the start of every task — **all steps are MANDATORY, in order, before writing any code**:
1. **Re-read AGENTS.md** — refresh all rules for this session
2. **Check GitNexus index freshness** — if available, verify index status
3. **Load the relevant skill(s)** from `.agent/skills/` and `.claude/skills/` based on task type (table below) via the `skill` tool — do this BEFORE starting the work, not after
4. **Before EVERY edit to a function/class/method/variable** — run `impact({target, direction})` on the target symbol; report blast radius to the user.
5. **If task is large (>=3 files, >=5 changes, or spans frontend+backend)** — create a hierarchical plan under `drafts/plans/<MMDDYY>_<n>_<status>/` with immutable IDs, exact files and verification steps, then **STOP in the same turn — do not implement yet; wait for the owner's approval**
6. **After implementation** — run the gates relevant to scope (`node scripts/verify.mjs`, pytest subset, `npm test`); on any failure fix until green and quote real output — never claim success from memory
7. **Before committing** — run `detect_changes()` to verify only expected symbols/flows changed

---

## 📋 Activation Report (MANDATORY at start of every task)

Before executing any implementation, display a brief **Activation Report** to the user:

```
📌 **Activation Report**
- **Rules:** [list of .agent/rules/ files loaded, e.g. AUTO_AGENT_LOADING.md, GEMINI.md]
- **Agent:** [e.g. backend-specialist, qa-reviewer, orchestrator]
- **Skills:** [list of skills applied, e.g. rag-advanced, ocr-processing, python-patterns, clean-code]
- **Workflow:** [e.g. plan.md, debug.md, enhance.md, or N/A]
- **Artifacts:** task.md ⬜ | implementation_plan.md ⬜
```

---

## Skill Auto-Selection by Task Type

| Task Type | Auto-load Skills |
|-----------|------------------|
| PDF Processing, OpenCV, PaddleOCR | `ocr-processing`, `python-patterns`, `clean-code` |
| Legal Document Structure, Chunking | `document-intelligence`, `python-patterns`, `clean-code` |
| RAG, Vector Search, Qdrant, Rerank | `rag-advanced`, `api-patterns`, `database-design` |
| Local/Cloud LLM Routing, LangGraph | `rag-advanced`, `api-patterns`, `python-patterns` |
| FastAPI / Backend API | `api-patterns`, `python-patterns`, `clean-code` |
| Frontend / React UI / OCR Review | **MANDATORY:** `impeccable`, `unslop` · (Optional / Reference: `ui-ux-pro-max`, `react-patterns`, `typescript-expert`, `clean-code`) |
| Database / PostgreSQL / Migrations | `database-design`, `clean-code` |
| Testing / RAGAS / OCR Benchmarks | `testing-patterns`, `pytest`, `tdd` |
| Debugging / Diagnostics | `diagnosing-bugs`, `systematic-debugging`, `clean-code` |
| Planning / Architecture | `writing-plans`, `architecture`, `to-spec` |
| GitNexus / Code Exploration | `gitnexus/gitnexus-exploring`, `gitnexus/gitnexus-impact-analysis` |

---

## 🎨 Mandatory Frontend Architecture & Design Rules

Mọi tác vụ chạm vào `frontend/` (React, UI components, styling, CSS, layout) **BẮT BUỘC** phải tuân thủ nghiêm ngặt:
1. **Load cặp đôi kỹ năng bắt buộc**: `impeccable` (kiến trúc layout, tokens, accessibility, components) và `unslop` (loại bỏ gradient tím/neon, bỏ hiệu ứng phát sáng lòe loẹt, chuẩn hóa quiet chrome, redline pass).
2. **Không tự ý code theo phong cách AI-Slop**: Tuyệt đối không dùng gradient lòe loẹt, emoji tràn lan ở tiêu đề, nút bấm pulsing, hoặc viền glow không cần thiết.
3. **Tra cứu quy chuẩn nếu cần**: Dùng `python .agent/skills/ui-ux-pro-max/scripts/search.py` để tra cứu nhanh bảng màu, typography hoặc quy tắc accessibility tương ứng.


---

## Hierarchical Plan for Large Tasks

When a task involves **>=3 files**, **>=5 distinct changes**, or **spans multiple components**, create a hierarchical plan:

```
1. [Component/Area]
   1.1. [Sub-task]
      1.1.1. [Specific action] — file: `path/to/file`
      1.1.2. [Specific action] — file: `path/to/file`
   1.2. [Sub-task]
2. [Component/Area]
   ...
```

---

## Plan & Task Documents Workflow

**MANDATORY**: Dù là tác vụ **PLAN** hay **FIX**, bắt buộc luôn tạo `implementation_plan.md` và `task.md` để theo dõi tiến độ:

1. Create `drafts/plans/` if it does not exist.
2. Create a timeline folder inside `drafts/plans/`:
   - Name format: `<MMDDYY>_<number>_<status>`
     - `<number>`: incrementing sequence starting at `01`
     - `<status>`: `draft` (new plan, work in progress), `done` (all tasks `[x]` + verification passed), `cancelled` (stopped by owner decision; append reason to `task.md`)
   - Example: `drafts/plans/112326_01_draft/`

---

## 🛡️ Mandatory Plan Grilling & Evaluation Angles Gate

Mỗi khi tạo plan mới trong `drafts/plans/<MMDDYY>_<n>_draft/implementation_plan.md`, **BẮT BUỘC** phải có 2 phần kiểm định sau đây trước khi dừng chờ Owner duyệt:

1. **Multi-Persona Evaluation Angles (3 Góc nhìn Chuyên môn Độc lập):**
   - **Data / Pipeline Angle (`data-pipeline-engineer`):** Đánh giá giới hạn RAM/VRAM (chống OOM 4GB), batching streaming, giải phóng buffer OpenCV/PyMuPDF, checkpoint resumable.
   - **OCR & Computer Vision Angle (`ocr-vision-specialist`):** Đánh giá độ nghiêng (deskew), denoise bảo toàn dấu tiếng Việt, PaddleOCR BGR shape, gom cụm bảng biểu (table structure) không làm gãy hàng/cột.
   - **Legal & Health Domain Angle (`legal-domain-specialist`):** Đánh giá bảo toàn cấu trúc Chương/Điều/Khoản/Điểm, chuẩn hóa Unicode NFC, metadata văn bản bãi bỏ/thay thế (`is_superseded`) và bảng điểm khám NVQS (Thông tư 105).

2. **Grilling Self-Check (Tự phản biện khắc nghiệt):**
   - Tự kích hoạt tư duy của skill `grilling` / `grill-with-docs` để chỉ ra ít nhất **3 Blindspots / Edge Cases** hóc búa nhất mà plan có thể gặp phải khi chạy thật.
   - Trả lời rõ ràng cách thức đối phó (Mitigation Strategy) cho từng blindspot ngay trong plan.

---

# Standing Rules (auto-applied every session — no need to repeat in prompts)

1. Read `drafts/WORKSPACE.md` for the familiar scope folders (read-only, do not modify/delete).
2. Read `docs/ai-context/ARCHITECTURE.md`, `docs/ai-context/API_MAP.md`, `docs/ai-context/FRONTEND_MAP.md` as needed — load the relevant context for the task at hand.
3. Detailed rules: `.agent/rules/AUTO_AGENT_LOADING.md` + `.agent/rules/GEMINI.md` — apply throughout the session.
4. Plan/task docs go under `drafts/plans/<MMDDYY>_<n>_<status>/` (see Plan & Task Documents Workflow above).
5. End of every task: report status (success/failure) + propose a Conventional Commits message.
6. Read `docs/ai-context/KNOWN_TRAPS.md` before fixing bugs — các lỗi cũ đã thành luật, đừng lặp lại.
7. Ticket ID bất biến: tham chiếu issue/task bằng ID (`KI-7`, `P2-9`) — cấm "mục trên/mục 2".
8. Load skill `clean-code` khi đang viết/sửa code — nó là thứ gối đầu khi đang code, AGENTS.md là hợp đồng.
9. Trước mỗi commit: chạy `node scripts/verify.mjs --only doc-truth` (node-only, vài giây — số trong docs phải khớp code, config: `kit.config.json`). Verify rộng hơn: `node scripts/verify.mjs --fast`; full suite chỉ khi đổi lớn.
10. Ticket MỚI theo lifecycle `docs/agents/issue-tracker-local.md`: file `docs/tickets/T-NNN-slug.md`, đổi trạng thái = RENAME `open-` → `doing-` → `done-`; label theo `docs/agents/triage-labels.md`.
11. Task lớn (≥3 file hoặc đa hệ): giao subagent kèm role card tương ứng trong `.claude/agents/` (be-engineer, fe-engineer, db-engineer, qa-reviewer, ...); lệnh verify của role lấy từ gates trong `kit.config.json`, không tự bịa.
12. Skills của repo: `.agent/skills` + `.claude/skills` là canonical. Thêm skill mới = cập nhật SKILL-SOURCES.md TRƯỚC, rồi mới drop folder.
13. **Push/PR/merge ≠ commit permission.** Chỉ commit khi owner nói rõ chữ "commit" trong chính turn đó. Nếu có thay đổi chưa commit mà owner chỉ bảo push/mở PR/merge, dừng lại và hỏi xin phép commit thay vì tự commit.
14. **Dual Database URL convention:** `DATABASE_URL_TEST` cho testing/local; `DATABASE_URL_PRODUCTION` cho production. Không hardcode chuỗi kết nối vào code logic.

---

# Workflow Contract (owner-approved pattern)

For every **non-trivial** request (code/config/docs/skill changes, or ≥3 files), follow this loop:

1. **Classify** — questions, read-only inspection/reports, and a clearly labelled one-line typo fix with "làm luôn" are exempt; when in doubt, plan.
2. **Plan first** — before any edit, create `implementation_plan.md` + `task.md` in `drafts/plans/<MMDDYY>_<n>_<status>/` with immutable IDs, exact files/interfaces and verification steps. Then **STOP** in the same turn — wait for owner approval.
3. **Execute after approval** — implement exactly the approved plan; surface any deviation first. When executing a ticket in `docs/tickets/`, rename `open-… → doing-…` at start and `doing-… → done-…` only after green verification. **State lives in the filename — never change it by editing the body.**
4. **Verify & repair** — run the gates relevant to scope; on failure, fix until all green; quote real command output — never claim success from memory.
5. **Sync Task & Plan Status (MANDATORY)** — ngay khi task và verify hoàn tất:
   - Đánh dấu `[x]` tất cả các task đã làm trong `drafts/plans/<MMDDYY>_<n>_<status>/task.md`.
   - Nếu toàn bộ sub-task trong plan đã xong, **BẮT BUỘC RENAME folder plan** từ `<MMDDYY>_<n>_draft` thành `<MMDDYY>_<n>_done`. Không được để tình trạng code xong mà plan vẫn gắn mác `_draft`.
6. **Stop clean** — when verification is green, stop. **Do NOT commit or push unless the owner explicitly asks in that same turn.** A push/PR/merge request does **NOT** imply commit permission — ask first when changes are uncommitted.

---

# Project Source of Truth — docs/ai-context/

`docs/ai-context/README.md` là điểm vào knowledge base **tracked trong git**:
ARCHITECTURE.md · MODULE_MAP.md · API_MAP.md · FRONTEND_MAP.md · TESTING_GUIDE.md ·
PROMPT_TEMPLATES.md · BEHAVIORAL_GUIDELINES.md · KNOWN_TRAPS.md · UI_UX_RULES.md ·
SKILL-SOURCES.md (manifest skills).
Docs mô tả code hiện tại — **khi mâu thuẫn, code đúng, docs sai** (và docs cần được cập nhật theo).

## Doc Trigger table — một điều kiện, hai chiều

| Task chạm vào... | BẮT BUỘC Đọc trước | BẮT BUỘC Cập nhật sau khi đổi |
|---|---|---|
| `backend/app/api/**` | `docs/ai-context/API_MAP.md` | API_MAP.md (endpoint mới/đổi shape) |
| `backend/app/services/**` hoặc `models/**` | `docs/ai-context/ARCHITECTURE.md` + `MODULE_MAP.md` | MODULE_MAP.md |
| `frontend/src/**` (routes/pages) | `docs/ai-context/FRONTEND_MAP.md` | FRONTEND_MAP.md |
| `backend/tests/**` hoặc thêm test | `docs/ai-context/TESTING_GUIDE.md` §1 | TESTING_GUIDE.md §1 (số test) |
| OCR, Ingestion, Preprocessing scripts | `docs/ai-context/MODULE_MAP.md` + `docs/ai-context/ARCHITECTURE.md` | MODULE_MAP.md |
| Debug / fix bug (đặc biệt bug lặp lại) | `docs/ai-context/KNOWN_TRAPS.md` | KNOWN_TRAPS.md |
| Viết/sửa UI, component, theme | `docs/ai-context/UI_UX_RULES.md` | UI_UX_RULES.md |
| Bất kỳ | `docs/ai-context/README.md` | README.md nếu summary stale |

**Khai báo bắt buộc**: dòng đầu của mỗi câu trả lời phải là:  
`Đã đọc: <danh sách file context đã load>` — biến "đã load context" thành kiểm chứng được.

---

## Known Operational Traps (đã từng cắn)

Bản đầy đủ (Triệu chứng → Root cause → Luật): **`docs/ai-context/KNOWN_TRAPS.md`**.

Tóm tắt 3 trap sống còn của Scan2RAG:
1. **4GB VRAM GPU OOM**: Chạy cùng lúc PaddleOCR + Embedding + Local LLM tràn VRAM. Khắc phục: Phân pha Offline Ingestion & Online Serving riêng biệt; giới hạn local model $\le 3B$ Q4_K_M.
2. **Vỡ cấu trúc bảng khám sức khỏe**: Quét OCR dòng ngang làm gãy liên kết bệnh tật - cột điểm (Thông tư 105). Khắc phục: Layout parsing sang Markdown/HTML table trước khi chunking; đối soát human-in-the-loop.
3. **Xung đột hiệu lực văn bản cũ - mới**: Trả lời nhầm quy định cũ của TT 105 thay vì TT 106 sửa đổi. Khắc phục: Ưu tiên Văn bản hợp nhất (VBHN 88); gắn metadata `is_superseded`.

---

## Quick facts — Scan2RAG

| Chỉ số | Giá trị | Phép đo |
|---|---|---|
| Apps | `backend` (FastAPI/Python), `frontend` (React/TypeScript) | Cấu trúc repo |
| Local LLM | LM Studio (`http://localhost:1234/v1`, Qwen2.5 1.5B/3B Q4_K_M) | Port local server |
| Cloud LLM | Free Tier (Groq API: `llama-3.3-70b-versatile`, OpenRouter `:free`) | API calls |
| Ingestion & OCR | PyMuPDF, OpenCV (deskew, denoise), PaddleOCR (Vietnamese) | Pipeline module |
| Vector & DB | Qdrant (Vector search), PostgreSQL (`DATABASE_URL_TEST` / `DATABASE_URL_PRODUCTION`) | Database layer |
| Verification Gate | `node scripts/verify.mjs` | Gate runner |

---

## Commit Message Convention & Language

- **Format:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `style:`, `docs:`, `test:`, `perf:` + scope <= 72 chars)
- **Chat language:** Vietnamese
- **Code, identifiers, technical docs:** English
