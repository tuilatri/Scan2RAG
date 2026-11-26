from unittest.mock import Mock

from app.agents.planner import parse_plan, plan_subqueries

QUERY = "So sánh Thông tư 105 và Thông tư 106"


def _router(content=None, side_effect=None):
    router = Mock()
    if side_effect is not None:
        router.generate.side_effect = side_effect
    else:
        router.generate.return_value = {"content": content or ""}
    return router


def test_valid_json_uses_llm_plan():
    content = (
        '```json\n{"documents": ["Thông_tư_105", "Thông_tư_106", "bad_doc"], '
        '"sub_queries": [{"question": "Cận thị TT105?"}, {"question": "Cận thị TT106?"}]}\n```'
    )
    router = _router(content)
    plan = plan_subqueries(QUERY, router)
    assert plan["source"] == "llm"
    assert plan["documents"] == ["thông_tư_105", "thông_tư_106"]
    assert len(plan["sub_queries"]) == 2
    assert router.generate.call_count == 1


def test_garbage_json_falls_back_to_deterministic():
    assert parse_plan("not json") == ([], [])
    assert parse_plan('{"documents": [], "sub_queries": []}') == ([], [])
    router = _router("plain text answer")
    plan = plan_subqueries(QUERY, router)
    assert plan["source"] == "deterministic"
    assert "thông_tư_105" in plan["documents"]


def test_llm_exception_falls_back_without_retry():
    router = _router(side_effect=RuntimeError("LLM down"))
    plan = plan_subqueries(QUERY, router)
    assert plan["source"] == "deterministic"
    assert router.generate.call_count == 1
    assert len(plan["sub_queries"]) == len(plan["documents"])
