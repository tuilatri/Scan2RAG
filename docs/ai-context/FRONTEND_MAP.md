# FRONTEND_MAP — Scan2RAG

> **What goes here:** routes → implementing files, key components, UI conventions, lib helpers and state/data patterns.
> Updated for Milestone 3 (React 19 + TypeScript + Vite + Tailwind CSS + Modular shadcn/ui).

## 1. Views & Layout Architecture
| View / Tab | Component File | Description |
|---|---|---|
| Main App Shell | `frontend/src/App.tsx` | App root with view switcher, chat stream, and pdf viewer integration |
| Header Navigation | `frontend/src/components/layout/navbar.tsx` | Top header with logo, version tag, backend status, and tab switcher |
| Dual-Pane Splitter | `frontend/src/components/layout/split-pane.tsx` | Responsive 2-column flex pane (Chat left, PDF right) with collapse trigger |
| RAG Chat Interface | `frontend/src/components/chat/chat-container.tsx` | Chat stream container with message list, suggestions, and auto-scroll |
| Synchronized PDF Viewer | `frontend/src/components/pdf/pdf-viewer-panel.tsx` | PDF toolbar, canvas iframe, and document metadata summary |
| OCR HITL Review | `frontend/src/components/ocr/ocr-review-container.tsx` | Table sidebar (111 tables), interactive grid editor, diff view, and PDF page preview |

## 2. Key Components Directory
- **`src/components/ui/` (Atomic shadcn/ui primitives - 1 file per component):**
  - `button.tsx`: CVA variant buttons (default, secondary, outline, ghost, destructive).
  - `card.tsx`: Card, CardHeader, CardTitle, CardContent, CardFooter.
  - `badge.tsx`: Status tags (default, secondary, outline, destructive).
  - `input.tsx` & `textarea.tsx`: Form inputs with focus-ring styling.
  - `scroll-area.tsx`: Radix UI scroll container.
  - `tabs.tsx`: Radix UI tab navigator.
  - `separator.tsx`: Layout divider.
  - `skeleton.tsx`: Loading shimmer placeholder.
  - `thin-scroll-area.tsx`: Radix ScrollArea wrapper with a 6px thumb, transparent track and no arrow buttons.

- **`src/components/chat/` (Conversational UI):**
  - `chat-container.tsx`: Main chat scroll area and input footer.
  - `chat-message.tsx`: Markdown rendered bubble with avatar and model router badge.
  - `chat-input.tsx`: Auto-resizing textarea, `suggestion-strip.tsx` (thin horizontal scroller) and filter switch.
  - `citation-list.tsx` & `citation-card.tsx`: Grounded citations with Amber Warning Badge for superseded laws.
  - `model-badge.tsx`: Visual tag distinguishing Local Qwen2.5 vs cloud. Cloud label is derived from the SSE `provider` string (`groq_cloud`→Groq, `openrouter_cloud`→OpenRouter, `gemini_cloud`→Gemini, `deterministic_offline`→Offline) — not hardcoded.
  - `stream-indicator.tsx`: Live SSE streaming status indicator.

- **`src/components/pdf/` (Document Preview):**
  - `pdf-viewer-panel.tsx`: Metadata, open-tab action and inline iframe canvas.
  - `pdf-canvas.tsx`: Iframe viewer with page jump (`#page=N`) and text snippet highlight.
  - `pdf-open-tab-button.tsx`: Opens the PDF in a new Chrome tab for the full native toolbar (zoom, fit, rotate, download, print).
  - `document-meta-card.tsx`: Legal validity summary (VBHN 88 priority, TT 105 superseded note).

- **`src/components/ocr/` (Human-in-the-Loop Rectification):**
  - `ocr-review-container.tsx`: Master workbench uniting sidebar, editor, and PDF preview.
  - `table-sidebar.tsx` & `table-sidebar-item.tsx`: Filterable list of 111 extracted medical tables.
  - `table-editor-panel.tsx` & `table-cell-editor.tsx`: Editable data table with military score (1-6) validation.
  - `table-diff-viewer.tsx`: Side-by-side comparison (Raw OCR vs VLM Rectified).
  - `table-toolbar.tsx`: Action toolbar (Save & Approve, Revert Raw, Revert Saved).
  - `page-preview-card.tsx`: Original PDF page iframe for visual eye-balling.

## 3. UI Conventions & Design System
- **Style Standard**: Strictly adheres to `impeccable` and `unslop` principles.
- **Palette**: Quiet Chrome enterprise palette (Slate/Zinc neutral base, Primary: Deep Royal Blue `hsl(221, 83%, 40%)`, Accent: Emerald `hsl(142, 71%, 45%)`, Warning: Amber `hsl(38, 92%, 50%)`).
- **Forbidden Patterns**: No purple/neon gradients, no glowing borders, no unnecessary pulsing badges, no excessive title emojis.
- **Responsiveness**: Dual-Pane split on desktop (`>= 1024px`), collapsible full-width pane on mobile/tablet.

## 4. State & Data Patterns
- **`useChatStream` (`src/hooks/use-chat-stream.ts`)**: Custom React hook managing Server-Sent Events (SSE) from `POST /api/v1/query/stream`. Handles `status` event for immediate UI feedback (< 1.0s TTFT), `citations` event after retrieval/rerank (~1.5–3s warm on CPU), token-by-token streaming, and 65s timeout watchdog (65000ms inactivity).
- **`usePdfViewer` (`src/hooks/use-pdf-viewer.ts`)**: Manages active document ID, current page, zoom level, and click-to-sync from chat citations.
- **`useOcrAudit` (`src/hooks/use-ocr-audit.ts`)**: Manages 111 table nodes, active table detail, cell matrix editing, Undo/Redo, and atomic backend saves.
- **`markdown-table-parser.ts` (`src/lib/markdown-table-parser.ts`)**: Bi-directional parser converting between Markdown Table string and 2D Array matrix.
