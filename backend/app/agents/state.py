"""State contract for the multi-document comparison graph."""

from typing import Any, TypedDict


class CompareState(TypedDict, total=False):
    query: str
    sub_queries: list[str]
    target_docs: list[str]
    evidence: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    evidence_summary: list[dict[str, Any]]
    missing: list[str]
    retry_count: int
    answer: str
    provider: str
    model: str
