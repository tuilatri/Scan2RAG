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


class TableMetadata(BaseModel):
    """Strongly typed schema for table node metadata to prevent silent key mismatch."""

    rows_count: int = 0
    cols_count: int = 0
    vlm_rectified: bool = False
    vlm_model: str | None = None
    rectify_time_sec: float | None = None
    raw_content_backup: str | None = None
    vlm_rejected: bool = False
    vlm_error: str | None = None


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

    def get_table_metadata(self) -> TableMetadata:
        """Extracts validated TableMetadata from the underlying dictionary."""
        return TableMetadata.model_validate(self.metadata)


class ParsedDocument(BaseModel):
    """Full structured document representation."""

    document_id: str
    document_name: str
    total_pages: int
    nodes: list[DocumentNode]
    summary_stats: dict[str, int | float | str] = Field(default_factory=dict)
