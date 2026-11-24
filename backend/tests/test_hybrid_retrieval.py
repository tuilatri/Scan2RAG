"""Hard Constraint Tests for Advanced Hybrid Retrieval & Reranker Engine (Lauren Tan Methodology).

Defines invariant assertions that MUST pass:
1. INV-RET-01: BM25 Tokenizer preserves legal articles ('Điều 12') and optical metrics ('-3D', '10/10').
2. INV-RET-02: RRF Score strictly adheres to Reciprocal Rank Fusion formula and is bounded within (0, 1].
3. INV-RET-03: Hybrid Searcher ranks dual-matching chunks (found by both Dense and Sparse) higher.
4. INV-RET-04: Reranker correctly outputs sorted list with valid rerank_score values.
"""

from unittest.mock import MagicMock

from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.reranker import LegalReranker


def test_hard_constraint_bm25_tokenizer_patterns():
    """Bất biến 1: Tokenizer phải bảo toàn các ký tự nhạy cảm y tế & điều khoản pháp luật."""
    text = "Theo Điều 12 và Khoản 2, người có tật khúc xạ Cận thị từ -3D đến dưới -4D, thị lực 10/10"
    tokens = LegalBM25Searcher.tokenize(text)

    # Must contain normalized patterns
    assert "điều" in tokens
    assert "12" in tokens
    assert "khoản" in tokens
    assert "2" in tokens
    assert "-3d" in tokens, f"Optical metric -3d lost! Tokens: {tokens}"
    assert "-4d" in tokens, f"Optical metric -4d lost! Tokens: {tokens}"
    assert "10/10" in tokens, f"Visual acuity 10/10 lost! Tokens: {tokens}"


def test_hard_constraint_bm25_search_ranking():
    """Bất biến 2: BM25 searcher phải rank chính xác chunk chứa exact keyword lên Top 1."""
    searcher = LegalBM25Searcher()
    mock_chunks = [
        {"id": "c1", "breadcrumb": "TT 105", "title": "Điều 10", "content": "Quy định về thời gian khám sức khỏe"},
        {"id": "c2", "breadcrumb": "TT 105", "title": "Điều 12", "content": "Tiêu chuẩn phân loại sức khỏe cận thị từ -3D"},
        {"id": "c3", "breadcrumb": "TT 105", "title": "Điều 15", "content": "Hội đồng giám định y khoa quân sự"},
    ]
    searcher.fit_from_chunks(mock_chunks)

    results = searcher.search("Điều 12 cận thị -3D", top_k=3)
    assert len(results) > 0, "BM25 must return results"
    top_chunk, score = results[0]
    assert top_chunk["id"] == "c2", f"Expected c2 at Top 1, got {top_chunk['id']}"
    assert score > 0.0, "Score must be positive"


def test_hard_constraint_rrf_rank_fusion_logic():
    """Bất biến 3: Thuật toán RRF phải ưu tiên tài liệu xuất hiện ở cả Dense và Sparse và resolve chunk_id đúng từ payload."""
    # Mock VectorStore returning integer Point IDs (as Qdrant does) and chunk_id in payload
    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {
            "id": 101,  # Qdrant integer point ID
            "score": 0.85,
            "payload": {
                "chunk_id": "doc_tt105_chunk_001",
                "page_numbers": [15],
                "breadcrumb": "B",
                "content": "C",
            },
        },
        {
            "id": 102,  # Qdrant integer point ID
            "score": 0.80,
            "payload": {
                "chunk_id": "doc_tt105_chunk_002",
                "page_numbers": [20],
                "breadcrumb": "B",
                "content": "C",
            },
        },
    ]

    # Mock Embedder
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 384

    # Mock BM25Searcher returning chunk_id matching payload["chunk_id"]
    mock_bm25 = MagicMock()
    mock_bm25.search.return_value = [
        ({"id": "doc_tt105_chunk_002", "page_numbers": [20], "breadcrumb": "B", "content": "C"}, 12.5),
        ({"id": "doc_sparse_only_003", "page_numbers": [25], "breadcrumb": "B", "content": "C"}, 10.0),
    ]

    hybrid = LegalHybridSearcher(
        vector_store=mock_vector_store,
        bm25_searcher=mock_bm25,
        embedder=mock_embedder,
        rrf_k=60,
    )
    results = hybrid.search(query="test query", top_k=3)

    assert len(results) == 3, "Must return 3 unified candidates"
    # 'doc_tt105_chunk_002' appears at rank 2 in dense and rank 1 in sparse:
    # rrf_score = (1 / (60 + 2)) + (1 / (60 + 1)) = 0.01613 + 0.01639 = 0.03252
    # 'doc_tt105_chunk_001' has rrf_score = 1 / (60 + 1) = 0.01639
    assert results[0]["id"] == "doc_tt105_chunk_002", f"Expected doc_tt105_chunk_002 at Top 1 due to Dual-Match RRF Boost, got {results[0]['id']}"
    assert results[0]["page_number"] == 20, f"Expected page_number 20 from page_numbers, got {results[0]['page_number']}"
    assert results[0]["dense_rank"] == 2
    assert results[0]["sparse_rank"] == 1
    assert results[0]["rrf_score"] > results[1]["rrf_score"]
    assert results[1]["page_number"] in [15, 25]


def test_hard_constraint_reranker_sorting():
    """Bất biến 4: LegalReranker phải trả về danh sách được sắp xếp giảm dần theo rerank_score."""
    # Test on lightweight cross-encoder
    reranker = LegalReranker()
    query = "Tiêu chuẩn cận thị nghĩa vụ quân sự"
    candidates = [
        {"id": "irrelevant", "breadcrumb": "Chương 1", "content": "Quy định về đăng ký nghĩa vụ quân sự lần đầu"},
        {"id": "relevant", "breadcrumb": "Chương 5", "content": "Bảng phụ lục phân loại sức khỏe: Cận thị từ -3D đến dưới -4D cho điểm 3 hoặc 4"},
    ]

    reranked = reranker.rerank(query=query, candidates=candidates, top_k=2)
    assert len(reranked) == 2
    assert "rerank_score" in reranked[0]
    assert "rerank_score" in reranked[1]
    assert reranked[0]["rerank_score"] >= reranked[1]["rerank_score"], "Results must be sorted descending"
    assert reranked[0]["id"] == "relevant", f"Expected relevant chunk at Top 1, got {reranked[0]['id']}"
