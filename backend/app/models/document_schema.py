"""Document schemas for structured legal parsing and metadata normalization."""

from enum import StrEnum

from pydantic import BaseModel, Field


class HierarchyLevel(StrEnum):
    DOCUMENT = "DOCUMENT"
    CHAPTER = "CHAPTER"
    SECTION = "SECTION"
    ARTICLE = "ARTICLE"
    CLAUSE = "CLAUSE"
    POINT = "POINT"
    TABLE = "TABLE"


class DocumentNode(BaseModel):
    """Hierarchical node representing a legal document component."""

    id: str = Field(..., description="Unique node identifier")
    document_id: str
    document_name: str
    level: HierarchyLevel
    title: str = ""
    content: str = ""
    page_number: int
    parent_id: str | None = None
    order: int = 0
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """Full structured document representation."""

    document_id: str
    document_name: str
    total_pages: int
    nodes: list[DocumentNode]
    summary_stats: dict[str, int] = Field(default_factory=dict)
