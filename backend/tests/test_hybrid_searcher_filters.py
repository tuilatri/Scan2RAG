"""Unit tests for Legal Hierarchy, article_id, breadcrumb, and HybridSearcher filters (Audit Group 4)."""

from unittest.mock import MagicMock

from app.chunking.semantic_chunker import SemanticLegalChunker
from app.retrieval.hybrid_searcher import LegalHybridSearcher


def test_semantic_chunker_breadcrumb_no_document_literal_and_ancestor_article_id():
    """Chunker must not emit literal 'DOCUMENT' in breadcrumb and must resolve ancestor ARTICLE id."""
    doc_data = {
        "document_id": "thông_tư_88",
        "document_name": "Thông tư 88",
        "nodes": [
            {"id": "art_5", "level": "ARTICLE", "title": "Điều 5", "content": "Nội dung điều 5", "parent_id": None, "page_number": 4},
            {"id": "clause_1", "level": "CLAUSE", "title": "Khoản 1", "content": "Nội dung khoản 1", "parent_id": "art_5", "page_number": 4},
            {"id": "doc_leaf", "level": "DOCUMENT", "title": "", "content": "Đoạn văn bản tự do", "parent_id": None, "page_number": 2},
        ],
    }
    chunker = SemanticLegalChunker()
    chunks = chunker.chunk_document(doc_data)

    clause_chunk = next(c for c in chunks if "Khoản 1" in c.breadcrumb)
    assert clause_chunk.article_id == "art_5"

    leaf_chunk = next(c for c in chunks if "Đoạn văn bản tự do" in c.content)
    assert "DOCUMENT" not in leaf_chunk.breadcrumb
    assert "Trang 2" in leaf_chunk.breadcrumb
    assert leaf_chunk.article_id is None


def test_hybrid_searcher_hard_filters_superseded_and_document_id_and_boosts_vbhn88():
    """filter_superseded=True must drop superseded TT105 chunks, and document_id must filter dense+sparse."""
    mock_vs = MagicMock()
    mock_vs.search.return_value = [
        {"id": "old_1", "score": 0.9, "payload": {"chunk_id": "old_1", "document_id": "thông_tư_105", "is_superseded": True, "content": "Cũ"}},
        {"id": "new_88", "score": 0.8, "payload": {"chunk_id": "new_88", "document_id": "thông_tư_88", "is_superseded": False, "content": "Mới 88"}},
        {"id": "new_106", "score": 0.85, "payload": {"chunk_id": "new_106", "document_id": "thông_tư_106", "is_superseded": False, "content": "Mới 106"}},
    ]
    mock_bm25 = MagicMock()
    mock_bm25.search.return_value = []

    searcher = LegalHybridSearcher(vector_store=mock_vs, bm25_searcher=mock_bm25)

    res = searcher.search("cận thị", top_k=5, filter_superseded=True)
    ids = [r["id"] for r in res]
    assert "old_1" not in ids
    assert ids[0] == "new_88"  # Boosted VBHN 88

    res_doc = searcher.search("cận thị", top_k=5, filter_superseded=True, document_id="thông_tư_106")
    assert [r["id"] for r in res_doc] == ["new_106"]
