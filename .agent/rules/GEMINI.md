# GEMINI.md — Universal AI Agent Behavior Rules

> Loaded automatically via `AGENTS.md` → Standing Rules.
> Works across all AI tools (OpenCode, Gemini, Claude, Cursor, etc.).

---

## Language Handling

When user's prompt is NOT in English:
1. **Internally translate** for better comprehension
2. **Respond in user's language** — match their communication
3. **Code comments, variable names, commit messages** remain in English

---

## Request Classifier

**Before ANY action, classify the request:**

| Request Type | Trigger Keywords | Result |
|--------------|------------------|--------|
| **QUESTION** | "what is", "how does", "explain" | Text response only |
| **SURVEY** | "analyze", "list files", "overview" | Report, no file changes |
| **SIMPLE CODE** | "fix", "add", "change" (single file) | Inline edit |
| **COMPLEX CODE** | "build", "create", "implement", "refactor" | Plan first, then code |
| **DESIGN/UI** | "design", "UI", "page", "dashboard" | Plan first, then code |

---

## Socratic Gate (For Complex Requests)

Before executing complex tasks, **STOP and ASK first:**

1. **Rule Acknowledgement** — which skills/rules apply to this task
2. **Phase Breakdown** — how you will tackle it
3. **Clarifying Questions** — at least 2 questions about edge cases, scope, or impact

| Request Type | Strategy | Required Action |
|--------------|----------|-----------------|
| New Feature / Build | Deep Discovery | Ask 3+ strategic questions |
| Code Edit / Bug Fix | Context Check | Confirm understanding + impact |
| Vague / Simple | Clarification | Ask purpose, users, scope |
| "Proceed" / "Go ahead" | Validation | Ask 2 edge-case questions before starting |

**Protocol:** Do NOT write code until the user explicitly clears the gate (e.g., "proceed", "ok", "yes").

---

## Clean Code Standards

All code must follow these principles:
- **Minimum code** that solves the problem. Nothing speculative.
- **No features** beyond what was asked.
- **No over-commenting** — code should be self-documenting.
- **No over-engineering** — no abstractions for single-use code.
- **Surgical changes** — touch only what you must. Don't "improve" adjacent code.
- **Match existing style** — even if you'd do it differently.
- **Remove only what YOUR changes made unused** — don't delete pre-existing dead code.

---

## Task Completion Gate

Before reporting a task as complete:

1. **Reference what changed** — list the files/sections modified
2. **Write Git Commit Message** — Conventional Commits format, max 72 chars
3. **Append the commit message** at the end of your completion response

Format:
```
✅ Task Complete
- Files changed: [list]
- Commit: `feat(scope): short description`
```

If no commit message is provided, the task is NOT considered complete.

---

## Project Conventions

- **Architecture:** See `AGENTS.md` for project scope and rules
- **Prompts:** Use templates in `drafts/PROMPT_TEMPLATES.md`
- **Plan/Task docs:** `drafts/plans/<MMDDYY>_<n>_<status>/`
- **Git commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`, `style:`, `docs:`, `test:`, `perf:`)

---

## What NOT To Do

- Do NOT load files/paths that don't exist in this project
- Do NOT reference agent names, scripts, or skills that aren't in `.agent/skills/`
- Do NOT apply rules from other projects (Purple Ban, Template Ban, game dev, 3D, mobile-specific)
- Do NOT use mixed languages in rules — keep English for consistency
