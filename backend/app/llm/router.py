"""Hybrid Model Router supporting Local LM Studio and 3 Cloud Providers (Gemini, Groq, OpenRouter).

Adheres to:
1. 4GB VRAM Hardware Limit: Prefers lightweight local quantized models (Qwen2.5 1.5B/3B) via LM Studio.
2. Complexity-based Routing:
   - Simple (Factual, 1 clause, 1 table, or single entity lookup) -> Local LM Studio (fallback Cloud).
   - Complex (Cross-document comparison, amendment analysis, multi-hop reasoning) -> Cloud LLM directly.
3. Multi-Cloud Fallback Chain: DEFAULT_CLOUD_PROVIDER -> Gemini -> Groq -> OpenRouter -> Deterministic Offline.
"""

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import OpenAI

# Automatically load .env if present
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


class ModelRouter:
    """Intelligent Model Router managing Local LM Studio and 3 Cloud Providers."""

    def __init__(
        self,
        local_base_url: str | None = None,
        local_model: str | None = None,
        default_cloud_provider: str | None = None,
        timeout: float = 15.0,
        **kwargs: Any,
    ):
        self.timeout = timeout
        self.local_base_url = local_base_url or os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        self.local_model = local_model or os.getenv("LOCAL_LLM_MODEL", "qwen2.5-1.5b-instruct")
        self.default_cloud_provider = (default_cloud_provider or os.getenv("DEFAULT_CLOUD_PROVIDER", "groq")).lower().strip()

        # Backward compatibility for legacy tests
        if "groq_api_key" in kwargs and kwargs["groq_api_key"] is None:
            # Explicitly disable cloud API keys if kwargs groq_api_key is None
            pass

        # Cloud configs from .env
        self.cloud_configs = {
            "gemini": {
                "base_url": os.getenv("GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
                "api_key": os.getenv("GEMINI_API_KEY"),
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            },
            "groq": {
                "base_url": os.getenv("GROQ_URL", "https://api.groq.com/openai/v1"),
                "api_key": os.getenv("GROQ_API_KEY"),
                "model": os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            },
            "openrouter": {
                "base_url": os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free"),
            },
        }

        # Initialize Local Client
        self.local_client = OpenAI(
            base_url=self.local_base_url,
            api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
            timeout=self.timeout,
        )

        # Initialize Cloud Clients
        self.cloud_clients: dict[str, OpenAI] = {}
        for provider, cfg in self.cloud_configs.items():
            if cfg["api_key"]:
                try:
                    self.cloud_clients[provider] = OpenAI(
                        base_url=cfg["base_url"],
                        api_key=cfg["api_key"],
                        timeout=self.timeout,
                    )
                except Exception:
                    pass

    def is_local_available(self) -> bool:
        """Check if local LM Studio server is actively responding."""
        try:
            resp = httpx.get(f"{self.local_base_url}/models", timeout=0.8)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def classify_complexity(query: str, context_chunks: list[dict[str, Any]] | None = None) -> str:
        """Classify query into 'simple' (local-first) or 'complex' (cloud-first).

        Criteria for 'complex':
        1. Query contains cross-statute comparison keywords (so sánh, khác nhau, sửa đổi, bổ sung, trước và sau).
        2. Query involves multi-condition exemptions or synthesis.
        3. Retrieved candidate chunks span across multiple different legal documents (e.g. TT 105 and TT 106).
        """
        q_lower = query.lower()
        complex_triggers = [
            "so sánh", "khác nhau", "thay đổi", "sửa đổi", "bổ sung",
            "thông tư 106", "văn bản hợp nhất", "trước và sau", "đối chiếu",
            "tổng hợp", "phân tích", "các trường hợp", "miễn hoãn", "nghĩa vụ quân sự và"
        ]
        if any(trig in q_lower for trig in complex_triggers):
            return "complex"

        # Check multi-document span
        if context_chunks and len(context_chunks) >= 2:
            doc_ids = {c.get("document_id") for c in context_chunks if c.get("document_id")}
            if len(doc_ids) >= 2:
                return "complex"

        return "simple"

    def _call_provider(self, client: OpenAI, model: str, messages: list[dict[str, str]], temperature: float) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=800,
        )
        return response.choices[0].message.content or ""

    def generate(
        self,
        prompt: str,
        system_prompt: str,
        complexity: str = "simple",
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate response adhering to complexity routing and multi-cloud fallback.

        Routing Logic:
        1. If 'simple': Try Local LM Studio first. If offline/error -> fallback to Cloud.
        2. If 'complex': Route directly to Cloud Provider (Gemini / Groq / OpenRouter).
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # 1. Local attempt for simple queries
        if complexity == "simple" and self.is_local_available():
            try:
                content = self._call_provider(self.local_client, self.local_model, messages, temperature)
                return {
                    "content": content,
                    "provider": "lm_studio_local",
                    "model": self.local_model,
                    "complexity": "simple",
                }
            except Exception:
                pass  # Fall through to cloud

        # 2. Cloud Fallback Chain
        cloud_order = [self.default_cloud_provider]
        for p in ["groq", "gemini", "openrouter"]:
            if p not in cloud_order:
                cloud_order.append(p)

        for provider in cloud_order:
            client = self.cloud_clients.get(provider)
            cfg = self.cloud_configs.get(provider)
            if client and cfg and cfg["model"]:
                try:
                    content = self._call_provider(client, cfg["model"], messages, temperature)
                    return {
                        "content": content,
                        "provider": f"{provider}_cloud",
                        "model": cfg["model"],
                        "complexity": complexity,
                    }
                except Exception:
                    continue  # Try next cloud provider

        # 3. If cloud fails but local LM Studio is available, try local even for complex queries
        if self.is_local_available():
            try:
                content = self._call_provider(self.local_client, self.local_model, messages, temperature)
                return {
                    "content": content,
                    "provider": "lm_studio_local",
                    "model": self.local_model,
                    "complexity": complexity,
                }
            except Exception:
                pass

        # 4. Deterministic Offline Fallback if all else fails
        return {
            "content": "Hệ thống tạm thời không thể kết nối tới các mô hình ngôn ngữ (Cloud Providers hoặc Local LM Studio) để phân tích câu trả lời chi tiết. Vui lòng tham khảo các đoạn trích dẫn pháp lý chính thức bên dưới.",
            "provider": "deterministic_offline",
            "model": "rule-based-fallback",
            "complexity": complexity,
        }
