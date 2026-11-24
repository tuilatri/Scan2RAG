"""Pydantic schema for Legal Chunk in Scan2RAG (Milestone 2).

Defines structured semantic chunks with legal hierarchy breadcrumbs,
provenance metadata, and vector indexing attributes.
"""

from typing import Any

from pydantic import BaseModel, Field


class LegalChunk(BaseModel):
    id: str = Field(..., description="Unique chunk ID, e.g. thông_tư_105_chunk_0042")
    document_id: str = Field(..., description="Source document identifier")
    document_name: str = Field(..., description="Human-readable document name")
    breadcrumb: str = Field(
        ...,
        description="Full hierarchy path, e.g. Thông tư 105 > Chương II > Điều 4 > Khoản 1"
    )
    hierarchy_path: list[str] = Field(
        default_factory=list,
        description="List of ancestor titles or levels"
    )
    content: str = Field(..., description="Chunk text content formatted cleanly")
    char_count: int = Field(default=0, description="Length in characters")
    token_count: int = Field(default=0, description="Approximate word/token count")
    is_table: bool = Field(default=False, description="Whether this chunk represents an atomic table")
    page_numbers: list[int] = Field(
        default_factory=list,
        description="List of PDF pages this chunk covers"
    )
    article_id: str | None = Field(default=None, description="Enclosing article ID if applicable")
    is_superseded: bool = Field(default=False, description="Whether this legal text is superseded")
    superseded_by: str | None = Field(default=None, description="Document ID that amends/supersedes this chunk")
    effective_date: str | None = Field(default=None, description="Effective legal date (YYYY-MM-DD)")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional indexing metadata"
    )
