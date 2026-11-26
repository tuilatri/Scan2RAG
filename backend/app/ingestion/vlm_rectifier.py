"""Vision-Language Model (VLM) verifier module.

Uses local multimodal models (e.g. Qwen-VL via LM Studio) to inspect scanned document
images and rectify OCR text/tables, enforcing strict numeric and structural consistency.
"""

import base64
import re
from collections import Counter
from typing import Any

import requests
from dotenv import dotenv_values

from app.core.paths import ENV_FILE


class VLMVerifier:
    """Verifies and rectifies OCR-extracted text against original page images using VLM."""

    SYSTEM_PROMPT = (
        "Bạn là chuyên gia rà soát văn bản pháp luật và y tế quân sự Việt Nam. "
        "Nhiệm vụ: Nhìn vào hình ảnh trang văn bản và đối chiếu với văn bản OCR thô được cung cấp. "
        "Hãy hiệu chỉnh, khôi phục ĐẦY ĐỦ VÀ CHÍNH XÁC dấu tiếng Việt (thanh, mũ) và sửa các lỗi OCR nhận diện sai, "
        "giữ nguyên cấu trúc Bảng Markdown Table, bảo toàn 100% các con số điểm (1, 2, 3, 4, 5, 6, 1T, 2T, 3T, 4T, 5T, 6T), "
        "và tuyệt đối không tự bịa đặt nội dung mới ngoài trang văn bản."
    )

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: int = 180,
    ):
        env = dotenv_values(str(ENV_FILE))
        self.base_url = (base_url or env.get("LM_STUDIO_BASE_URL") or "http://localhost:1234/v1").rstrip("/")
        self.api_key = api_key or env.get("LM_STUDIO_API_KEY") or "lm-studio"
        self.model_name = model_name or env.get("LOCAL_VLM_MODEL") or "qwen/qwen3-vl-4b"
        self.timeout = timeout

    @staticmethod
    def extract_numbers(text: str) -> list[str]:
        """Extracts all standalone numbers, decimals, percentages, and military grade notations (e.g. 1.5, 3T, 85%)."""
        pattern = re.compile(r"\b\d+(?:\.\d+)?(?:[Tt]|%)?")
        return [n.upper() for n in pattern.findall(text) if n.strip()]

    def verify_numbers_preserved(
        self, original_text: str, rectified_text: str
    ) -> tuple[bool, str | None]:
        """Ensures all essential numeric and medical grades in original text are preserved 100%.

        Uses Counter to ensure:
        1. No numbers are lost or duplicated (frequency matches 100%).
        2. No foreign hallucinated numbers are added.
        Returns (is_valid, error_reason).
        """
        orig_nums = self.extract_numbers(original_text)
        if not orig_nums:
            return True, None

        rect_nums = self.extract_numbers(rectified_text)

        orig_counter = Counter(orig_nums)
        rect_counter = Counter(rect_nums)

        lost_numbers = orig_counter - rect_counter
        added_numbers = rect_counter - orig_counter

        if lost_numbers or added_numbers:
            reasons = []
            if lost_numbers:
                lost_str = ", ".join(f"{k} (mất {v})" for k, v in lost_numbers.items())
                reasons.append(f"Mất số: [{lost_str}]")
            if added_numbers:
                added_str = ", ".join(f"{k} (thêm {v})" for k, v in added_numbers.items())
                reasons.append(f"Tự bịa số lạ: [{added_str}]")
            return False, "; ".join(reasons)

        return True, None

    @staticmethod
    def clean_markdown_response(response_text: str) -> str:
        """Extracts pure markdown table or text from LLM response, stripping conversational wraps."""
        text = response_text.strip()
        fence_match = re.search(r"```(?:markdown)?\s*\n(.*?)\n```", text, re.DOTALL)
        if fence_match:
            return fence_match.group(1).strip()

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        pipe_lines = [row_line for row_line in lines if row_line.startswith("|") and row_line.endswith("|")]
        if len(pipe_lines) >= 2:
            return "\n".join(pipe_lines)

        return text

    def _call_api(self, messages: list[dict[str, Any]]) -> str:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2048,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
        result = resp.json()
        return result["choices"][0]["message"]["content"]

    def rectify_page_content(
        self,
        image_bytes: bytes,
        raw_content: str,
        content_type: str = "TABLE",
        max_retries: int = 1,
    ) -> dict[str, Any]:
        """Sends page image and OCR raw text to local VLM for rectification with retry and strict 100% number safeguard."""
        if not raw_content.strip():
            return {"success": True, "content": raw_content, "error": None}

        base64_img = base64.b64encode(image_bytes).decode("utf-8")

        raw_lines = raw_content.split("\n")
        truncated_raw = "\n".join(raw_lines[:80])
        prompt_instruction = (
            f"Dưới đây là nội dung OCR thô dạng {content_type} của trang văn bản:\n\n"
            f"```markdown\n{truncated_raw}\n```\n\n"
            "Hãy nhìn vào ảnh và xuất lại nội dung này với đầy đủ dấu tiếng Việt chuẩn xác 100%, "
            "giữ nguyên cấu trúc Markdown (đảm bảo mọi hàng đều có cùng số cột |) và BẮT BUỘC giữ nguyên 100% tất cả các con số, điểm số:"
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_instruction},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
                ],
            },
        ]

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                raw_output = self._call_api(messages)
                cleaned_output = self.clean_markdown_response(raw_output)

                is_valid, error_msg = self.verify_numbers_preserved(raw_content, cleaned_output)
                if is_valid:
                    return {"success": True, "content": cleaned_output, "error": None}

                last_error = f"Safeguard vi phạm: {error_msg}"

                # If failed on first attempt, retry with targeted correction prompt
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": raw_output})
                    retry_feedback = (
                        f"CẢNH BÁO: Bạn vừa làm sai lệch các con số so với bản gốc ({error_msg}). "
                        "Hãy xuất lại bảng Markdown, TUYỆT ĐỐI giữ nguyên đầy đủ tất cả con số từ bản gốc:"
                    )
                    messages.append({"role": "user", "content": retry_feedback})

            except Exception as e:
                last_error = f"Request exception: {e}"

        return {
            "success": False,
            "content": raw_content,
            "error": last_error,
        }
