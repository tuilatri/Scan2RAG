import sys
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "backend"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.agents.compare_graph import build_compare_graph  # noqa: E402
from app.agents.verification import extract_numbers, unsupported_numbers  # noqa: E402
from scripts.audit_processed_data import extract_numbers as audit_extract_numbers  # noqa: E402

CHUNK_105 = {"id": "c105", "document_id": "thông_tư_105", "content": "Cận thị 3 điểm", "breadcrumb": "TT105"}
CHUNK_106 = {"id": "c106", "document_id": "thông_tư_106", "content": "Quy định mới", "breadcrumb": "TT106"}
QUERY = "So sánh Thông tư 105 và Thông tư 106"


def test_number_extraction_matches_audit_helper():
    samples = (
        "Cận thị -3D đến dưới -4D: 3 điểm",
        "Thị lực 10/10, điểm 6T",
        "BMI 18,5%",
    )
    for text in samples:
        assert extract_numbers(text) == audit_extract_numbers(text)
    assert unsupported_numbers("Theo TT105: 7 điểm", "Cận thị 3 điểm " + QUERY) == {"7": 1}


def _graph(generate_side_effect):
    searcher = Mock()
    searcher.search.return_value = []
    reranker = Mock()
    reranker.rerank.side_effect = [[CHUNK_105], [CHUNK_106]]
    router = Mock()
    router.generate.side_effect = generate_side_effect
    return build_compare_graph(searcher, reranker, router), router


def test_unsupported_number_is_flagged_and_regenerated_once():
    bad = {"content": "Theo TT105: 7 điểm", "provider": "lm_studio_local", "model": "qwen"}
    good = {"content": "Theo TT105: 3 điểm", "provider": "lm_studio_local", "model": "qwen"}
    graph, router = _graph([bad, good])
    result = graph.invoke({"query": QUERY})
    assert router.generate.call_count == 2
    assert result["verify_count"] == 2  # verify trước + verify sau regenerate
    assert result["verification"]["passed"] is True
    assert "CHỈ dùng số liệu" in router.generate.call_args_list[1].kwargs["prompt"]


def test_verification_is_bounded_when_model_keeps_hallucinating():
    bad = {"content": "Theo TT105: 7 điểm", "provider": "lm_studio_local", "model": "qwen"}
    graph, router = _graph([bad, bad])
    result = graph.invoke({"query": QUERY})
    assert router.generate.call_count == 2
    assert result["verify_count"] == 2
    assert result["verification"]["passed"] is False
    assert "7" in result["verification"]["unsupported_numbers"]
