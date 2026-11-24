"""Document Serving Endpoints for Scan2RAG (Milestone 3).

Provides endpoints to list legal documents and stream raw PDF files with HTTP 206 Partial Content (Range bytes) support.
"""

import os
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

# Base data directory where raw PDFs are stored
RAW_DOCS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw"

# Canonical Document Catalog with Legal Metadata
DOCUMENT_CATALOG = [
    {
        "id": "thông_tư_88",
        "file_name": "Thông_tư_88.pdf",
        "title": "Thông tư số 88/VBHN-BQP (Văn bản hợp nhất)",
        "effective_date": "2023-12-31",
        "is_superseded": False,
        "description": "Văn bản hợp nhất quy định tiêu chuẩn sức khỏe, khám sức khỏe thực hiện nghĩa vụ quân sự.",
        "pages_count": 120,
    },
    {
        "id": "thông_tư_105",
        "file_name": "Thông_tư_105.pdf",
        "title": "Thông tư số 105/2023/TT-BQP",
        "effective_date": "2023-12-06",
        "is_superseded": True,
        "superseded_by": "Thông tư 106/2024/TT-BQP & VBHN 88",
        "description": "Quy định tiêu chuẩn sức khỏe, khám sức khỏe thực hiện nghĩa vụ quân sự (đã được sửa đổi).",
        "pages_count": 105,
    },
    {
        "id": "thông_tư_106",
        "file_name": "Thông_tư_106.pdf",
        "title": "Thông tư số 106/2024/TT-BQP",
        "effective_date": "2024-05-15",
        "is_superseded": False,
        "description": "Sửa đổi, bổ sung một số điều của Thông tư số 105/2023/TT-BQP.",
        "pages_count": 50,
    },
    {
        "id": "thông_tư_68",
        "file_name": "Thông_tư_68.pdf",
        "title": "Thông tư số 68/2020/TT-BQP",
        "effective_date": "2020-05-20",
        "is_superseded": False,
        "description": "Quy định chi tiết việc thi hành một số điều của Luật Nghĩa vụ quân sự.",
        "pages_count": 6,
    },
    {
        "id": "hướng_dẫn_cục_quân_y",
        "file_name": "Hướng_dẫn_Cục_quân_y.pdf",
        "title": "Hướng dẫn số 259/HD-QY Cục Quân Y",
        "effective_date": "2024-01-10",
        "is_superseded": False,
        "description": "Hướng dẫn chuyên môn về phân loại thể lực và khám bệnh chuyên khoa phục vụ tuyển quân.",
        "pages_count": 6,
    },
]


class DocumentMeta(BaseModel):
    id: str
    file_name: str
    title: str
    effective_date: str
    is_superseded: bool
    superseded_by: str | None = None
    description: str
    pages_count: int
    size_bytes: int = 0


@router.get("", response_model=list[DocumentMeta])
def list_documents() -> list[dict[str, Any]]:
    """Return the list of all registered legal documents with their metadata."""
    results = []
    for doc in DOCUMENT_CATALOG:
        doc_copy = dict(doc)
        file_path = RAW_DOCS_DIR / doc["file_name"]
        if file_path.exists():
            doc_copy["size_bytes"] = file_path.stat().st_size
        else:
            doc_copy["size_bytes"] = 0
        results.append(doc_copy)
    return results


@router.get("/{doc_id}")
def get_document_info(doc_id: str) -> dict[str, Any]:
    """Return metadata for a specific document by ID."""
    doc_id_normalized = doc_id.lower().strip()
    for doc in DOCUMENT_CATALOG:
        if doc["id"].lower() == doc_id_normalized or doc["file_name"].lower() == doc_id_normalized:
            doc_copy = dict(doc)
            file_path = RAW_DOCS_DIR / doc["file_name"]
            doc_copy["size_bytes"] = file_path.stat().st_size if file_path.exists() else 0
            return doc_copy
    raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")


@router.get("/{doc_id}/pdf")
def stream_document_pdf(
    doc_id: str,
    request: Request,
    range: str | None = Header(None),
) -> Response:
    """Serve PDF file with HTTP 206 Partial Content (Range requests) support for seamless viewer streaming."""
    doc_id_normalized = doc_id.lower().strip()
    target_doc = None
    for doc in DOCUMENT_CATALOG:
        if doc["id"].lower() == doc_id_normalized or doc["file_name"].lower() == doc_id_normalized:
            target_doc = doc
            break

    if not target_doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    file_path = RAW_DOCS_DIR / target_doc["file_name"]
    # Path traversal protection
    try:
        resolved_path = file_path.resolve()
        if not str(resolved_path).startswith(str(RAW_DOCS_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied: Invalid path traversal attempt.")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid path.") from e

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file for '{doc_id}' does not exist on disk.")

    file_size = os.path.getsize(file_path)
    safe_filename = urllib.parse.quote(target_doc["file_name"])

    # If no Range header, return standard FileResponse
    if not range:
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}",
            },
        )

    # Parse Range: bytes=start-end
    try:
        range_val = range.strip().replace("bytes=", "")
        parts = range_val.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            return Response(
                status_code=416,
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        content_length = end - start + 1
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(content_length)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "application/pdf",
            "Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}",
        }
        return Response(content=data, status_code=206, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process Range request: {str(e)}") from e
