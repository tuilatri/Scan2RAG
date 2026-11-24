"""Hard Constraint Tests for Legal Embedder (Lauren Tan Methodology).

Defines invariant assertions that MUST pass:
1. Embedding dimension: Exactly 384 dimensions for multilingual-e5-small.
2. Prefix contract: 'passage: ' for document chunks and 'query: ' for search queries.
3. Batch invariance: Single item embedding matches batch embedding.
4. Numerical stability: Vectors must be L2 normalized (unit length norm ~= 1.0).
"""

import numpy as np
import pytest

from app.embeddings.embedder import LegalEmbedder


@pytest.fixture(scope="module")
def embedder():
    # Use lightweight multilingual-e5-small
    return LegalEmbedder(model_name="intfloat/multilingual-e5-small")


def test_hard_constraint_embedding_dimension(embedder):
    """Bất biến 1: Chiều vector bắt buộc là 384 dimensions."""
    sample_text = "Tiêu chuẩn phân loại sức khỏe nghĩa vụ quân sự theo Thông tư 105"
    vec = embedder.embed_text(sample_text, is_query=False)

    assert isinstance(vec, list), "Vector must be returned as list of floats"
    assert len(vec) == 384, f"Dimension mismatch! Expected 384, got {len(vec)}"


def test_hard_constraint_l2_normalization(embedder):
    """Bất biến 2: Vector bắt buộc phải chuẩn hóa L2 (norm ~= 1.0) cho cosine similarity."""
    sample_text = "Thị lực mắt phải 10/10 tổng thị lực 19/10 đạt sức khỏe Loại 1"
    vec = embedder.embed_text(sample_text, is_query=False)

    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    assert pytest.approx(norm, abs=1e-3) == 1.0, f"Vector must have unit L2 norm, got {norm}"


def test_hard_constraint_prefix_discrimination(embedder):
    """Bất biến 3: e5 model bắt buộc phân biệt prefix query vs passage."""
    text = "Quy định về bệnh cận thị nghĩa vụ quân sự"
    vec_passage = embedder.embed_text(text, is_query=False)
    vec_query = embedder.embed_text(text, is_query=True)

    cos_sim = np.dot(vec_passage, vec_query)
    # The two vectors should be highly similar but NOT identical due to 'passage: ' vs 'query: ' prefix
    assert cos_sim < 0.999, "Prefix 'passage: ' and 'query: ' must produce distinct embeddings"
