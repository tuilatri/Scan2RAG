import re
import unicodedata


class TextNormalizer:
    """Normalizes Vietnamese legal text extracted via OCR.

    - Unicode NFC normalization
    - Common legal abbreviation and OCR typo corrections
    - Noise artifact removal from signatures/stamps
    - Roman numeral header preservation (avoids confusion with clause numbers)
    """

    TYPO_CORRECTIONS: dict[str, str] = {
        r"\bHà Ni\b": "Hà Nội",
        r"\bca B trưng\b": "của Bộ trưởng",
        r"\bca Bộ trưởng\b": "của Bộ trưởng",
        r"\bca B\b": "của Bộ",
        r"\bB Quc phòng\b": "Bộ Quốc phòng",
        r"\bB Quốc phòng\b": "Bộ Quốc phòng",
        r"\bB Quốc phng\b": "Bộ Quốc phòng",
        r"\bBO QUÓC PHÒNG\b": "BỘ QUỐC PHÒNG",
        r"\bThông tu\b": "Thông tư",
        r"\bThng tư\b": "Thông tư",
        r"\bNgh định\b": "Nghị định",
        r"\bQuyt định\b": "Quyết định",
        r"\bCăn c\b": "Căn cứ",
        r"\bĐiu\b": "Điều",
        r"\bđiu\b": "điều",
        r"\biu\b": "Điều",
        r"\bKhon\b": "Khoản",
        r"\bkhon\b": "khoản",
        r"\bđim\b": "điểm",
        r"\bSa đi, b sung\b": "Sửa đổi, bổ sung",
        r"\bSra đi, b sung\b": "Sửa đổi, bổ sung",
    }

    # Match Roman numerals at line start before an uppercase title, e.g. "1. TIÊU CHUẨN" -> "I. TIÊU CHUẨN"
    ROMAN_HEADER_PATTERN = re.compile(
        r"^([1I|])\.\s+([A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]{4,})",
        re.MULTILINE,
    )

    def normalize(self, text: str) -> str:
        """Apply comprehensive normalization pipeline."""
        if not text:
            return ""

        # 1. Unicode NFC Normalization
        text = unicodedata.normalize("NFC", text)

        # 2. Fix Roman numeral headers corrupted into "1." or "|."
        def fix_roman(match: re.Match[str]) -> str:
            prefix = match.group(1)
            title = match.group(2)
            if prefix in ("1", "|"):
                return f"I. {title}"
            return match.group(0)

        text = self.ROMAN_HEADER_PATTERN.sub(fix_roman, text)

        # 3. Apply common legal OCR dictionary corrections
        for pattern, replacement in self.TYPO_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 4. Clean up repetitive noisy scanner artifacts (e.g. "---", "___", excessive punctuation)
        text = re.sub(r"[_\-—]{4,}", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        return text.strip()
