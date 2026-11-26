from unittest.mock import Mock

from app.llm.router import ModelRouter


def _router(monkeypatch, *, local_available: bool, fail_providers: set[str]):
    router = ModelRouter()
    router.prefer_local = False
    monkeypatch.setattr(router, "is_local_available", lambda: local_available)

    cloud = {
        "groq": Mock(name="groq"),
        "gemini": Mock(name="gemini"),
        "openrouter": Mock(name="openrouter"),
    }
    router.cloud_clients = cloud
    calls: list[tuple[object, float | None]] = []

    def fake_stream(client, model, messages, temperature, timeout=None):
        calls.append((client, timeout))
        provider = next(
            (name for name, value in cloud.items() if value is client),
            "local" if client is router.local_client else "unknown",
        )
        if provider in fail_providers:
            raise RuntimeError("network down")
        yield "token"

    monkeypatch.setattr(router, "_call_provider_stream", fake_stream)
    return router, calls


def _stream(router):
    return list(router.generate_stream("câu hỏi", "system", complexity="complex"))


def test_local_fallback_runs_after_first_cloud_failure(monkeypatch):
    router, calls = _router(monkeypatch, local_available=True, fail_providers={"groq"})
    tokens = _stream(router)
    meta = tokens[-1][1]
    assert meta["provider"] == "lm_studio_local"
    assert meta["stage"] == "local_fallback"
    assert all(client is not router.cloud_clients["gemini"] for client, _ in calls)
    assert calls[0][1] == router.cloud_timeout
    assert calls[1][1] is None


def test_other_clouds_are_tried_when_local_unavailable(monkeypatch):
    router, calls = _router(monkeypatch, local_available=False, fail_providers={"groq"})
    tokens = _stream(router)
    meta = tokens[-1][1]
    assert meta["provider"] == "gemini_cloud"
    assert meta["stage"] == "cloud_failed"
    assert any(client is router.cloud_clients["gemini"] for client, _ in calls)


def test_offline_when_everything_fails(monkeypatch):
    router, _ = _router(
        monkeypatch,
        local_available=False,
        fail_providers={"groq", "gemini", "openrouter"},
    )
    tokens = _stream(router)
    meta = tokens[-1][1]
    assert meta["provider"] == "deterministic_offline"
    assert meta["stage"] == "offline"
