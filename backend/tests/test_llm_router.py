from unittest.mock import patch

from app.llm.router import ModelRouter


def test_classify_complexity_simple():
    router = ModelRouter()
    query = "Huyết áp bao nhiêu thì đạt loại 1?"
    chunks = [{"document_id": "thông_tư_105", "text": "Điều 5 quy định về phân loại sức khỏe..."}]
    complexity = router.classify_complexity(query, chunks)
    assert complexity == "simple"

def test_classify_complexity_complex():
    router = ModelRouter()
    query = "So sánh sự khác nhau giữa Thông tư 105 và thông tư mới về tiêu chuẩn cận thị?"
    chunks = [
        {"document_id": "thông_tư_105", "text": "Thông tư 105 quy định..."},
        {"document_id": "thông_tư_106", "text": "Thông tư khác..."}
    ]
    complexity = router.classify_complexity(query, chunks)
    assert complexity == "complex"

def test_router_initialization():
    router = ModelRouter()
    assert router.default_cloud_provider in ["groq", "gemini", "openrouter"]
    assert "groq" in router.cloud_configs
    assert "gemini" in router.cloud_configs
    assert "openrouter" in router.cloud_configs

def test_deterministic_offline_fallback():
    router = ModelRouter()
    # Mock all cloud clients to fail
    with patch.object(router, "is_local_available", return_value=False):
        with patch.object(router, "_call_provider", side_effect=Exception("API Error")):
            res = router.generate("Câu hỏi kiểm tra", "System prompt", complexity="complex")
            assert res["provider"] == "deterministic_offline"
            assert res["model"] == "rule-based-fallback"
            assert "Hệ thống tạm thời không thể kết nối" in res["content"]
