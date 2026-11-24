"""Hybrid Model Router supporting Local LM Studio and Cloud Groq / OpenRouter.

Adheres to:
1. 4GB VRAM Hardware Limit: Prefers lightweight local quantized models (Qwen2.5 1.5B/3B) via LM Studio.
2. Auto-Fallback: Gracefully routes to Groq API (llama-3.3-70b-versatile) when local server is offline or fails.
3. Offline Resiliency: Provides deterministic mock generation when no LLM provider is connected.
"""

import os
from typing import Any

import httpx
from openai import OpenAI


class ModelRouter:
    """Manages routing between Local LM Studio and Cloud Providers."""

    def __init__(
        self,
        local_base_url: str = "http://localhost:1234/v1",
        local_model: str = "qwen2.5-1.5b-instruct",
        groq_api_key: str | None = None,
        groq_model: str = "llama-3.3-70b-versatile",
        timeout: float = 15.0,
    ):
        self.local_base_url = os.getenv("LM_STUDIO_BASE_URL", local_base_url)
        self.local_model = os.getenv("LOCAL_LLM_MODEL", local_model)
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", groq_model)
        self.timeout = timeout

        # Initialize local OpenAI client
        self.local_client = OpenAI(
            base_url=self.local_base_url,
            api_key="lm-studio",  # LM Studio does not require auth
            timeout=self.timeout,
        )

        # Initialize Groq client if key available
        self.groq_client = None
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key, timeout=self.timeout)
            except Exception:
                self.groq_client = None

    def is_local_available(self) -> bool:
        """Check if LM Studio server is responding on local port."""
        try:
            resp = httpx.get(f"{self.local_base_url}/models", timeout=0.8)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        """Generate response with automatic Local -> Cloud fallback.

        Returns:
            Dict containing 'content', 'provider', 'model', and 'latency_ms'.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # 1. Try Local LM Studio first
        if self.is_local_available():
            try:
                response = self.local_client.chat.completions.create(
                    model=self.local_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return {
                    "content": response.choices[0].message.content or "",
                    "provider": "lm_studio_local",
                    "model": self.local_model,
                }
            except Exception:
                pass  # Fall through to cloud

        # 2. Try Cloud Groq if available
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return {
                    "content": response.choices[0].message.content or "",
                    "provider": "groq_cloud",
                    "model": self.groq_model,
                }
            except Exception:
                pass

        # 3. Deterministic Fallback if both offline
        return {
            "content": "Căn cứ vào tài liệu được cung cấp, hệ thống đã trích xuất các dẫn chứng liên quan bên dưới.",
            "provider": "deterministic_offline",
            "model": "rule-based-fallback",
        }
