"""Canonical Layer-A facts and rules used as graph input.

A chunk is evidence; a canonical fact is the decision-critical assertion that
the chunk supports. Nothing here is authoritative without human review.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CanonicalFact(BaseModel):
    id: str = Field(..., description="Stable fact id, e.g. TT105_p23_vision_19_10")
    document_id: str
    page: int = Field(..., ge=1)
    condition: str = Field(..., description="Human-readable condition, e.g. 'cận thị -3D đến dưới -4D'")
    value: float
    value_type: str = "score"
    source_kind: str = Field(..., description="pdf_text_layer | ocr | vlm | human")
    evidence_image: str = Field(..., description="Path to the rendered evidence crop")
    raw_row: str | None = None
    reviewer: str = "agent"
    needs_human: bool = True
    authoritative: bool = False
    valid_from: str | None = None
    superseded_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalRule(BaseModel):
    id: str
    document_id: str
    page: int = Field(..., ge=1)
    condition: str
    conclusion: str
    source_kind: str
    evidence_image: str
    raw_text: str
    reviewer: str = "agent"
    needs_human: bool = True
    authoritative: bool = False
    valid_from: str | None = None
    superseded_by: str | None = None
