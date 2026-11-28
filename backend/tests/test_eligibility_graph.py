import json

from app.graph.eligibility_graph import EligibilityGraph


def _graph(tmp_path):
    facts = tmp_path / "facts.json"
    rules = tmp_path / "rules.json"
    facts.write_text(json.dumps({"facts": [
        {
            "id": "f1", "document_id": "thông_tư_105", "page": 23,
            "condition": "- Viễn thị từ + 3D đến dưới + 4D", "value": 5,
            "authoritative": True, "evidence_image": "x.png",
        },
        {
            "id": "f2", "document_id": "thông_tư_105", "page": 23,
            "condition": "- Bị loại", "value": 6, "authoritative": False,
            "evidence_image": "x.png",
        },
    ]}), encoding="utf-8")
    rules.write_text(json.dumps({"rules": [{
        "id": "r1", "condition": "không gọi nhập ngũ", "page": 2,
        "raw_text": "Không gọi nhập ngũ đối với viễn thị các mức độ",
    }]}), encoding="utf-8")
    return EligibilityGraph.build(facts, rules)


def test_condition_kind_detection():
    assert EligibilityGraph.condition_kind("viễn thị có phải đi không") == "refraction"
    assert EligibilityGraph.condition_kind("loạn thị có phải đi không") == "astigmatism"
    assert EligibilityGraph.condition_kind("BMI dưới 18") == "bmi"


def test_supporting_facts_excludes_non_authoritative(tmp_path):
    graph = _graph(tmp_path)
    facts = graph.supporting_facts("viễn thị có phải đi không")
    assert [fact["id"] for fact in facts] == ["f1"]


def test_summary_contains_rule_and_fact_citations(tmp_path):
    graph = _graph(tmp_path)
    summary = graph.summary("viễn thị có phải đi không")
    assert "CANONICAL RULE CHAIN" in summary
    assert "trang 2" in summary
    assert "trang 23" in summary
    assert "5 điểm" in summary
