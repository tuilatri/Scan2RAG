"""Vision-Language Model (VLM) verifier module.

Uses local multimodal models (e.g. Qwen-VL via LM Studio) to inspect scanned document
images and rectify OCR text/tables, enforcing strict numeric and structural consistency.
"""

import base64
import re
from typing import Any

import requests
from dotenv import dotenv_values


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
        timeout: int = 150,
    ):
        env = dotenv_values(".env")
        self.base_url = (
            base_url or env.get("LM_STUDIO_BASE_URL") or "http://localhost:1234/v1"
        ).rstrip("/")
        self.api_key = api_key or env.get("LM_STUDIO_API_KEY") or "lm-studio"
        self.model_name = model_name or env.get("LOCAL_VLM_MODEL") or "qwen/qwen3-vl-4b"
        self.timeout = timeout

    @staticmethod
    def extract_numbers(text: str) -> list[str]:
        """Extracts all standalone numbers, decimals, and military grade notations (e.g. 1.5, 3T)."""
        # Match numbers with optional decimal, and military grades like 3T, 4T
        pattern = re.compile(r"\b\d+(?:\.\d+)?(?:T|t)?\b")
        return pattern.findall(text)

    def verify_numbers_preserved(
        self, original_text: str, rectified_text: str, tolerance: float = 0.90
    ) -> bool:
        """Ensures all essential numeric and medical grades in original text are preserved in rectified text.

        Returns True if at least tolerance (default 90%) of original numbers exist in rectified text.
        """
        orig_nums = self.extract_numbers(original_text)
        if not orig_nums:
            return True  # No numbers to protect

        rect_nums = set(self.extract_numbers(rectified_text))
        matched = sum(1 for n in orig_nums if n in rect_nums)
        ratio = matched / len(orig_nums)
        return ratio >= tolerance

    @staticmethod
    def clean_markdown_response(response_text: str) -> str:
        """Extracts pure markdown table or text from LLM response, stripping conversational wraps."""
        text = response_text.strip()
        # Extract markdown fence if present
        fence_match = re.search(r"```(?:markdown)?\s*\n(.*?)\n```", text, re.DOTALL)
        if fence_match:
            return fence_match.group(1).strip()

        # If it contains table pipes, trim before first pipe and after last pipe
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        pipe_lines = [row_line for row_line in lines if row_line.startswith("|") and row_line.endswith("|")]
        if len(pipe_lines) >= 2:
            return "\n".join(pipe_lines)

        return text

    def rectify_page_content(
        self,
        image_bytes: bytes,
        raw_content: str,
        content_type: str = "TABLE",
    ) -> dict[str, Any]:
        """Sends page image and OCR raw text to local VLM for rectification.

        Returns dict:
            - success: bool
            - content: str (rectified content or original if failed)
            - error: str | None
        """
        if not raw_content.strip():
            return {"success": True, "content": raw_content, "error": None}

        base64_img = base64.b64encode(image_bytes).decode("utf-8")

        prompt_instruction = (
            f"Dưới đây là nội dung OCR thô dạng {content_type} của trang văn bản:\n\n"
            f"```markdown\n{raw_content[:2000]}\n```\n\n"
            "Hãy nhìn vào ảnh và xuất lại nội dung này với đầy đủ dấu tiếng Việt chuẩn xác 100%, "
            "giữ nguyên cấu trúc Markdown và không đổi bất kỳ con số nào:"
        )

        user_content = [
            {"type": "text", "text": prompt_instruction},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
        ]

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return {
                    "success": False,
                    "content": raw_content,
                    "error": f"HTTP {resp.status_code}: {resp.text}",
                }

            result = resp.json()
            raw_output = result["choices"][0]["message"]["content"]
            cleaned_output = self.clean_markdown_response(raw_output)

            # Safeguard check: Verify numeric and score preservation
            if not self.verify_numbers_preserved(raw_content, cleaned_output):
                return {
                    "success": False,
                    "content": raw_content,
                    "error": "Safeguard triggered: Numeric discrepancies detected. Reverted to raw content.",
                }

            return {"success": True, "content": cleaned_output, "error": None}

        except Exception as e:
            return {
                "success": False,
                "content": raw_content,
                "error": f"Request exception: {e}",
            }
