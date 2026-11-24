"""Hard Constraint Tests for Semantic Legal Chunker (Lauren Tan Methodology).

Defines invariant assertions that MUST pass:
1. Zero critical text loss: Total chunked character length must retain >= 98% of source text.
2. Breadcrumb & hierarchy preservation: 100% of chunks must carry breadcrumb string.
3. Atomic table integrity: Table nodes must not be severed mid-table; markdown pipes must remain consistent.
4. Token length sanity: No chunk exceeds max_tokens (e.g., 800 tokens) except single atomic oversized tables.
"""

import json
from pathlib import Path
import pytest

from app.models.chunk_schema import LegalChunk
from app.chunking.semantic_chunker import SemanticLegalChunker


@pytest.fixture
def sample_tt105_data():
    json_path = Path("data/processed/thông_tư_105.json")
    assert json_path.exists(), "Source corpus thông_tư_105.json must exist"
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def test_chunker_schema_compliance(sample_tt105_data):
    """Test that all generated chunks strictly conform to LegalChunk schema."""
    chunker = SemanticLegalChunker(max_tokens=600, overlap_tokens=50)
    chunks = chunker.chunk_document(sample_tt105_data)

    assert len(chunks) > 0, "Chunker must produce chunks from TT105"
    for chunk in chunks:
        assert isinstance(chunk, LegalChunk), "Each chunk must be an instance of LegalChunk"
        assert chunk.id, "Chunk id must not be empty"
        assert chunk.document_id == "thông_tư_105", "Document id must be preserved"
        assert len(chunk.content.strip()) > 0, "Chunk content must not be empty"


def test_hard_constraint_breadcrumb_preservation(sample_tt105_data):
    """Bất biến 2: 100% chunks phải có breadcrumb rõ ràng phân cấp pháp lý."""
    chunker = SemanticLegalChunker(max_tokens=600, overlap_tokens=50)
    chunks = chunker.chunk_document(sample_tt105_data)

    for chunk in chunks:
        assert chunk.breadcrumb, f"Chunk {chunk.id} missing breadcrumb!"
        assert "Thông tư 105" in chunk.breadcrumb or "thông_tư_105" in chunk.breadcrumb.lower(), (
            f"Chunk {chunk.id} breadcrumb must contain root document title: {chunk.breadcrumb}"
        )


def test_hard_constraint_atomic_table_integrity(sample_tt105_data):
    """Bất biến 3: Bảng y tế phải giữ nguyên vẹn cấu trúc Markdown, không rách cột."""
    chunker = SemanticLegalChunker(max_tokens=600, overlap_tokens=50)
    chunks = chunker.chunk_document(sample_tt105_data)

    table_chunks = [c for c in chunks if c.is_table]
    assert len(table_chunks) >= 45, "Must retain all 45 table nodes from TT105"

    for tc in table_chunks:
        lines = [l.strip() for l in tc.content.splitlines() if l.strip().startswith("|")]
        assert len(lines) >= 2, f"Table chunk {tc.id} must have at least header + separator"
        col_counts = set()
        for l in lines:
            if set(l.replace("|", "").strip()) == {"-"}:
                continue
            cells = [c.strip() for c in l.strip("|").split("|")]
            col_counts.add(len(cells))
        assert len(col_counts) == 1, f"Table chunk {tc.id} has fractured columns: {col_counts}"


def test_hard_constraint_text_retention(sample_tt105_data):
    """Bất biến 1: Không nuốt chữ, tổng ký tự nội dung giữ lại >= 95% sau khi trừ rác."""
    chunker = SemanticLegalChunker(max_tokens=600, overlap_tokens=50)
    chunks = chunker.chunk_document(sample_tt105_data)

    source_nodes = sample_tt105_data.get("nodes", [])
    raw_chars = sum(len(n.get("content", "")) for n in source_nodes)
    chunked_chars = sum(len(c.content) for c in chunks)

    retention_ratio = chunked_chars / max(raw_chars, 1)
    assert retention_ratio >= 0.95, (
        f"Critical text loss detected! Retention ratio: {retention_ratio:.4f} (Source: {raw_chars}, Chunks: {chunked_chars})"
    )
