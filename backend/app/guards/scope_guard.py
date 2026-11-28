"""Deterministic guard for questions outside the legal/military-health corpus."""

from __future__ import annotations

SCOPE_REFUSAL_MESSAGE = (
    "Câu hỏi này nằm ngoài phạm vi tài liệu pháp lý/y tế quân sự của hệ thống."
)

OUT_OF_SCOPE_PATTERNS = (
    "thời tiết",
    "dự báo thời tiết",
    "nhiệt độ ngoài trời",
    "giá xe",
    "giá ô tô",
    "giá điện thoại",
    "giá vàng",
    "giá xăng",
    "giá cả",
    "đặt vé",
    "mua vé",
    "vé máy bay",
    "vé xe",
    "đặt phòng",
    "khách sạn",
    "chỉ số iq",
    "chỉ số thông minh",
    "tính iq",
    "bài thơ",
    "thơ ca",
    "sáng tác",
    "viết truyện",
    "bài hát",
    "bóng đá",
    "thể thao",
    "trận đấu",
    "tỷ số",
    "nấu ăn",
    "món ăn",
    "công thức nấu",
    "chứng khoán",
    "đầu tư",
    "tiền mã hoá",
    "crypto",
)

IN_SCOPE_HINTS = (
    "thông tư",
    "vbhn",
    "văn bản hợp nhất",
    "nghĩa vụ quân sự",
    "quân y",
    "khám sức khỏe",
    "khám sức khoẻ",
    "cận thị",
    "viễn thị",
    "bmi",
    "điểm",
    "điều ",
    "khoản ",
    "quy định",
    "bệnh",
    "phụ lục",
    "tiêu chuẩn sức khỏe",
    "tiêu chuẩn sức khoẻ",
    "miễn hoãn",
    "tạm hoãn",
)


def is_out_of_scope(query: str) -> bool:
    """True when the question is clearly unrelated to the corpus.

    In-scope legal/medical hints win over out-of-scope keywords, so a question
    like "thời tiết có ảnh hưởng đến khám sức khỏe không?" is not blocked.
    """
    text = " ".join(str(query or "").lower().split())
    if not text:
        return False
    if any(hint in text for hint in IN_SCOPE_HINTS):
        return False
    return any(pattern in text for pattern in OUT_OF_SCOPE_PATTERNS)
