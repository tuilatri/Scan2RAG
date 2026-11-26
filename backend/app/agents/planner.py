"""Opt-in LLM planner for the compare workflow, with deterministic fallback."""

import json
import os
import re
from typing import Any

ALLOWED_DOCS = (
    "thông_tư_105",
    "thông_tư_106",
    "thông_tư_88",
    "thông_tư_68",
    "hướng_dẫn_cục_quân_y",
)
DOCUMENT_TOKENS = (
    ("105", "thông_tư_105"),
    ("106", "thông_tư_106"),
    ("88", "thông_tư_88"),
    ("hợp nhất", "thông_tư_88"),
)
FALLBACK_DOCS = ("thông_tư_105", "thông_tư_106")
MAX_SUBQUERIES = 3
FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$")
PLANNER_SYSTEM_PROMPT = (
    "Bạn là bộ lập kế hoạch tra cứu văn bản pháp lý Việt Nam. "
    "Chỉ trả về JSON thuần, không markdown, theo dạng: "
    '{"documents": ["id"], "sub_queries": ["câu hỏi con"]}. '
    "id phải nằm trong danh sách cho phép. Tối đa 3 câu hỏi con."
)


def planner_enabled() -> bool:
    return os.getenv("PLANNER_LLM", "").strip().lower() in {"1", "true", "yes", "on"}


def detect_documents(query: str) -> list[str]:
    lowered = query.lower()
    found: list[str] = []
    for token, document_id in DOCUMENT_TOKENS:
        if token in lowered and document_id not in found:
            found.append(document_id)
    for document_id in FALLBACK_DOCS:
        if len(found) >= 2:
            break
        if document_id not in found:
            found.append(document_id)
    return found


def parse_plan(text: str) -> tuple[list[str], list[str]]:
    cleaned = FENCE_PATTERN.sub("", (text or "").strip()).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return [], []
    if not isinstance(data, dict):
        return [], []
    documents: list[str] = []
    for item in data.get("documents", []):
        if not isinstance(item, str):
            continue
        document_id = item.strip().lower()
        if document_id in ALLOWED_DOCS and document_id not in documents:
            documents.append(document_id)
    sub_queries: list[str] = []
    for item in data.get("sub_queries", []):
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get("question") or item.get("query") or item.get("text") or "").strip()
        else:
            continue
        if text and text not in sub_queries:
            sub_queries.append(text[:300])
    documents = documents[:MAX_SUBQUERIES]
    sub_queries = sub_queries[:MAX_SUBQUERIES]
    if not documents or not sub_queries:
        return [], []
    return documents, sub_queries


def _fallback(query: str) -> dict[str, Any]:
    documents = detect_documents(query)
    return {
        "documents": documents,
        "sub_queries": [f"{query} — {document_id}" for document_id in documents],
        "source": "deterministic",
    }


def plan_subqueries(query: str, model_router: Any) -> dict[str, Any]:
    try:
        result = model_router.generate(
            prompt=(
                f"Câu hỏi cần so sánh: {query}\n"
                f"Văn bản được phép: {', '.join(ALLOWED_DOCS)}"
            ),
            system_prompt=PLANNER_SYSTEM_PROMPT,
            complexity="simple",
            temperature=0.0,
        )
        documents, sub_queries = parse_plan(result.get("content", ""))
        if documents and sub_queries:
            return {"documents": documents, "sub_queries": sub_queries, "source": "llm"}
    except Exception:
        pass
    return _fallback(query)
