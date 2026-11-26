from unittest.mock import Mock, patch

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


def test_prefer_local_complex_uses_local(monkeypatch):
    monkeypatch.setenv("PREFER_LOCAL", "true")
    router = ModelRouter()
    with patch.object(router, "is_local_available", return_value=True), patch.object(
        router, "_call_provider", return_value="local answer"
    ):
        result = router.generate("Câu hỏi kiểm tra", "System prompt", complexity="complex")
    assert result["provider"] == "lm_studio_local"
    assert result["complexity"] == "complex"


def test_complex_without_prefer_local_uses_cloud(monkeypatch):
    monkeypatch.delenv("PREFER_LOCAL", raising=False)
    router = ModelRouter()
    router.cloud_clients = {"groq": Mock()}
    with patch.object(router, "_call_provider", return_value="cloud answer"):
        result = router.generate("Câu hỏi kiểm tra", "System prompt", complexity="complex")
    assert result["provider"] == "groq_cloud"
