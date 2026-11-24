"""OCR Table Audit & Human-in-the-Loop (HITL) Rectification Endpoints for Scan2RAG (Milestone 3).

Provides endpoints to:
1. List all 111 extracted medical/legal tables with their review status.
2. Get detailed table matrix, markdown, and raw OCR backup.
3. Submit human rectifications with validation guards and atomic file writes.
"""

import json
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/ocr", tags=["OCR HITL Rectification"])

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
_file_lock = threading.Lock()


class TableSummary(BaseModel):
    id: str
    document_id: str
    document_name: str
    page_number: int
    title: str
    rows_count: int
    cols_count: int
    vlm_rectified: bool = False
    hitl_approved: bool = False
    hitl_rectified: bool = False


class TableDetail(BaseModel):
    id: str
    document_id: str
    document_name: str
    page_number: int
    title: str
    content: str
    raw_content_backup: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RectifyRequest(BaseModel):
    content: str = Field(..., min_length=10, description="New rectified Markdown table string")
    approved: bool = Field(default=True, description="Mark as human approved")
    reviewer_notes: str | None = None


def parse_markdown_to_matrix(md_text: str) -> tuple[list[str], list[list[str]]]:
    """Parse Markdown table into headers and rows matrix."""
    lines = [line.strip() for line in md_text.strip().split("\n") if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 2:
        return [], []

    # First line is header
    raw_headers = [c.strip() for c in table_lines[0].strip("|").split("|")]

    # Skip delimiter line (| --- | --- |)
    rows = []
    for line in table_lines[1:]:
        if re.match(r"^\|(\s*:?-+:?\s*\|)+$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Pad or trim to match header length
        if len(cells) < len(raw_headers):
            cells += [""] * (len(raw_headers) - len(cells))
        elif len(cells) > len(raw_headers):
            cells = cells[:len(raw_headers)]
        rows.append(cells)

    return raw_headers, rows


@router.get("/tables", response_model=list[TableSummary])
def list_ocr_tables() -> list[dict[str, Any]]:
    """List all extracted tables across processed JSON files."""
    tables = []
    if not PROCESSED_DIR.exists():
        return []

    for file_path in sorted(PROCESSED_DIR.glob("*.json")):
        if file_path.name.startswith("."):
            continue
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            nodes = data.get("nodes", [])
            for node in nodes:
                if node.get("level") == "TABLE":
                    meta = node.get("metadata", {})
                    tables.append({
                        "id": node.get("id"),
                        "document_id": node.get("document_id"),
                        "document_name": node.get("document_name", ""),
                        "page_number": node.get("page_number", 1),
                        "title": node.get("title", ""),
                        "rows_count": meta.get("rows_count", 0),
                        "cols_count": meta.get("cols_count", 0),
                        "vlm_rectified": meta.get("vlm_rectified", False),
                        "hitl_approved": meta.get("hitl_approved", False),
                        "hitl_rectified": meta.get("hitl_rectified", False),
                    })
        except Exception:
            continue

    # Sort tables by document then page number
    tables.sort(key=lambda t: (t["document_id"], t["page_number"]))
    return tables


@router.get("/tables/{node_id}", response_model=TableDetail)
def get_ocr_table_detail(node_id: str) -> dict[str, Any]:
    """Get full details of a specific table node, including matrix format."""
    for file_path in sorted(PROCESSED_DIR.glob("*.json")):
        if file_path.name.startswith("."):
            continue
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            nodes = data.get("nodes", [])
            for node in nodes:
                if node.get("id") == node_id and node.get("level") == "TABLE":
                    content = node.get("content", "")
                    meta = node.get("metadata", {})
                    headers, rows = parse_markdown_to_matrix(content)
                    return {
                        "id": node.get("id"),
                        "document_id": node.get("document_id"),
                        "document_name": node.get("document_name", ""),
                        "page_number": node.get("page_number", 1),
                        "title": node.get("title", ""),
                        "content": content,
                        "raw_content_backup": meta.get("raw_content_backup"),
                        "headers": headers,
                        "rows": rows,
                        "metadata": meta,
                    }
        except Exception:
            continue

    raise HTTPException(status_code=404, detail=f"Table node '{node_id}' not found.")


@router.post("/tables/{node_id}/rectify")
def rectify_ocr_table(node_id: str, payload: RectifyRequest) -> dict[str, Any]:
    """Submit human rectification for a table, validating format and atomically updating JSON."""
    headers, rows = parse_markdown_to_matrix(payload.content)
    if not headers or len(headers) < 2:
        raise HTTPException(
            status_code=422,
            detail="Invalid Markdown Table format: Must contain at least a header row with 2+ columns.",
        )

    target_file = None
    target_data = None
    target_node = None

    with _file_lock:
        for file_path in sorted(PROCESSED_DIR.glob("*.json")):
            if file_path.name.startswith("."):
                continue
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                nodes = data.get("nodes", [])
                for node in nodes:
                    if node.get("id") == node_id and node.get("level") == "TABLE":
                        target_file = file_path
                        target_data = data
                        target_node = node
                        break
                if target_node:
                    break
            except Exception:
                continue

        if not target_node or not target_file:
            raise HTTPException(status_code=404, detail=f"Table node '{node_id}' not found.")

        # Update node fields
        meta = target_node.setdefault("metadata", {})
        # Keep original raw backup if not yet preserved
        if not meta.get("raw_content_backup"):
            meta["raw_content_backup"] = target_node.get("content", "")

        target_node["content"] = payload.content.strip()
        meta["hitl_rectified"] = True
        meta["hitl_approved"] = payload.approved
        meta["rows_count"] = len(rows)
        meta["cols_count"] = len(headers)
        if payload.reviewer_notes:
            meta["reviewer_notes"] = payload.reviewer_notes

        # Atomic write with backup
        tmp_file = target_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(target_data, f, ensure_ascii=False, indent=2)
            tmp_file.replace(target_file)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to write rectified data: {str(e)}") from e

    return {
        "status": "success",
        "node_id": node_id,
        "message": "Bảng dữ liệu đã được lưu và cập nhật thành công.",
        "rows_count": len(rows),
        "cols_count": len(headers),
        "hitl_approved": payload.approved,
    }
