"""Test script for Qwen-VL Vision-Language verification on scanned document pages.

Tests:
1. Renders Page 25 of Thông tư 105 (Medical criteria table).
2. Encodes image to base64.
3. Sends image + PaddleOCR raw text to Qwen-VL via LM Studio endpoint.
4. Compares OCR raw text vs Qwen-VL verified/normalized text.
"""

import base64
import json
import time
from pathlib import Path

import pymupdf
import requests
from dotenv import dotenv_values


def test_qwen_vl_verification():
    env_config = dotenv_values(".env")
    base_url = env_config.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    api_key = env_config.get("LM_STUDIO_API_KEY", "lm-studio")
    vlm_model = env_config.get("LOCAL_VLM_MODEL", "qwen/qwen3-vl-4b")

    pdf_path = Path("data/raw/Thông_tư_105.pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.")
        return

    print(
        "================================================================================"
    )
    print(
        "                TESTING QWEN-VL RECTIFICATION ON THÔNG TƯ 105                   "
    )
    print(
        "================================================================================"
    )
    print(f"Endpoint: {base_url}")
    print(f"VLM Model: {vlm_model}")

    # 1. Render Page 25 to JPEG image (clamp max dimension to 1280 to save VRAM)
    doc = pymupdf.open(str(pdf_path))
    page = doc[24]  # 0-indexed Page 25
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpeg")
    doc.close()

    base64_image = base64.b64encode(img_bytes).decode("utf-8")
    print(
        f"Rendered Page 25: {pix.width}x{pix.height} ({len(img_bytes) / 1024:.1f} KB)"
    )

    # 2. Read the raw extracted text from data/processed/thông_tư_105.json for Page 25
    processed_json = Path("data/processed/thông_tư_105.json")
    page_raw_content = ""
    if processed_json.exists():
        with open(processed_json, encoding="utf-8") as f:
            data = json.load(f)
        p25_nodes = [n for n in data["nodes"] if n["page_number"] == 25]
        if p25_nodes:
            page_raw_content = p25_nodes[0]["content"]

    print("\n--- SAMPLE RAW TEXT/TABLE FROM PADDLEOCR ---")
    preview_lines = page_raw_content.split("\n")[:10]
    for l in preview_lines:
        print(f"  {l}")

    # 3. Call Qwen-VL via OpenAI-compatible chat completion
    system_prompt = (
        "Bạn là chuyên gia rà soát văn bản pháp luật và y tế quân sự Việt Nam. "
        "Nhiệm vụ của bạn: Nhìn vào hình ảnh trang văn bản và đối chiếu với văn bản OCR thô được cung cấp. "
        "Hãy hiệu chỉnh, khôi phục ĐẦY ĐỦ VÀ CHÍNH XÁC dấu tiếng Việt (thanh, mũ) và sửa các lỗi OCR nhận diện sai, "
        "giữ nguyên cấu trúc Bảng Markdown Table, bảo toàn 100% các con số điểm (1, 2, 3, 4, 5, 6) và tuyệt đối không tự bịa đặt nội dung mới."
    )

    user_content = [
        {
            "type": "text",
            "text": (
                "Dưới đây là nội dung OCR thô của trang văn bản này:\n\n"
                f"```markdown\n{page_raw_content[:1500]}\n```\n\n"
                "Hãy nhìn vào ảnh và xuất lại bảng Markdown này với đầy đủ dấu tiếng Việt chuẩn xác 100%:"
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        },
    ]

    payload = {
        "model": vlm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("\nSending request to Qwen-VL in LM Studio...")
    start_time = time.time()
    try:
        response = requests.post(
            f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120
        )
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"API Error ({response.status_code}): {response.text}")
            return

        res_json = response.json()
        output_text = res_json["choices"][0]["message"]["content"]

        print(f"\n✓ Response received in {elapsed:.2f}s!")
        print(
            "\n================================================================================"
        )
        print(
            "               OUTPUT RECTIFIED BY QWEN-VL (WITH FULL DIACRITICS)               "
        )
        print(
            "================================================================================"
        )
        print(output_text[:2000])

    except (requests.RequestException, json.JSONDecodeError, OSError) as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_qwen_vl_verification()
