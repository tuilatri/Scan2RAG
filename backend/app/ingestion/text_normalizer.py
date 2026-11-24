import re
import unicodedata


class TextNormalizer:
    """Normalizes Vietnamese legal text extracted via OCR.

    - Unicode NFC normalization
    - Common legal and medical abbreviation and OCR typo corrections
    - Noise artifact removal from signatures/stamps
    - Roman numeral header preservation (avoids confusion with clause numbers)
    """

    TYPO_CORRECTIONS: dict[str, str] = {
        # Administrative & Government entities
        r"\bChính ph\b": "Chính phủ",
        r"\bChính ph quy đnh\b": "Chính phủ quy định",
        r"\bHà Ni\b": "Hà Nội",
        r"\bca B trưng\b": "của Bộ trưởng",
        r"\bca Bộ trưởng\b": "của Bộ trưởng",
        r"\bca B\b": "của Bộ",
        r"\bB trưng\b": "Bộ trưởng",
        r"\bB trung\b": "Bộ trưởng",
        r"\bQuc phòng\b": "Quốc phòng",
        r"\bB Quc phòng\b": "Bộ Quốc phòng",
        r"\bB Quốc phòng\b": "Bộ Quốc phòng",
        r"\bB Quốc phng\b": "Bộ Quốc phòng",
        r"\bBO QUÓC PHÒNG\b": "BỘ QUỐC PHÒNG",
        r"\bTng cc Hu cn\b": "Tổng cục Hậu cần",
        r"\bTng cc Hu cn - K thut\b": "Tổng cục Hậu cần - Kỹ thuật",
        r"\bTng Tham mưu trưng\b": "Tổng Tham mưu trưởng",
        r"\bco quan\b": "cơ quan",
        r"\bt chc\b": "tổ chức",
        r"\bco cáu\b": "cơ cấu",
        r"\bco cu\b": "cơ cấu",
        r"\bco cáu t chc\b": "cơ cấu tổ chức",
        r"\bco cu t chc\b": "cơ cấu tổ chức",
        r"\bchc năng, nhim v, quyn hn\b": "chức năng, nhiệm vụ, quyền hạn",
        r"\bnhim v\b": "nhiệm vụ",
        r"\bquyn hn\b": "quyền hạn",
        # Statutory terms
        r"\bThông tu\b": "Thông tư",
        r"\bThng tư\b": "Thông tư",
        r"\bNgh định\b": "Nghị định",
        r"\bNgh đnh\b": "Nghị định",
        r"\bQuyt định\b": "Quyết định",
        r"\bQuyt đnh\b": "Quyết định",
        r"\bCăn c\b": "Căn cứ",
        r"\bCăn cú\b": "Căn cứ",
        r"\bquy đnh\b": "quy định",
        r"\bban hành\b": "ban hành",
        r"\bĐiu\b": "Điều",
        r"\bđiu\b": "điều",
        r"\biu\b": "Điều",
        r"\bKhon\b": "Khoản",
        r"\bkhon\b": "khoản",
        r"\bđim\b": "điểm",
        r"\bSa đi, b sung\b": "Sửa đổi, bổ sung",
        r"\bSra đi, b sung\b": "Sửa đổi, bổ sung",
        r"\bthc hin\b": "thực hiện",
        r"\báp dng\b": "áp dụng",
        # Medical & Military Health Examination terms
        r"\bsúc khóe\b": "sức khỏe",
        r"\bsúc khõe\b": "sức khỏe",
        r"\bsc khóe\b": "sức khỏe",
        r"\bsc khe\b": "sức khỏe",
        r"\bsc khõe\b": "sức khỏe",
        r"\bkhám súc khóe\b": "khám sức khỏe",
        r"\bkhám sc khóe\b": "khám sức khỏe",
        r"\bkhám sc khe\b": "khám sức khỏe",
        r"\btiêu chun súc khóe\b": "tiêu chuẩn sức khỏe",
        r"\btiêu chun sc khe\b": "tiêu chuẩn sức khỏe",
        r"\btiêu chun\b": "tiêu chuẩn",
        r"\bphân loi\b": "phân loại",
        r"\bBnh tt\b": "Bệnh tật",
        r"\bbnh tt\b": "bệnh tật",
        r"\bChi tiêu\b": "Chỉ tiêu",
        r"\bchi tiêu\b": "chỉ tiêu",
        r"\bth thúy tinh\b": "thể thủy tinh",
        r"\bth thy tinh\b": "thể thủy tinh",
        r"\bĐuc thê thúy tinh\b": "Đục thể thủy tinh",
        r"\bĐuc th thy tinh\b": "Đục thể thủy tinh",
        r"\bLch th thy tinh\b": "Lệch thể thủy tinh",
        r"\bLch th\b": "Lệch thể",
        r"\bLch\b": "Lệch",
        r"\bvõng mc\b": "võng mạc",
        r"\bBong võng mc\b": "Bong võng mạc",
        r"\bviêm màng b đào\b": "viêm màng bồ đào",
        r"\bViêm màng b đào\b": "Viêm màng bồ đào",
        r"\bđái tháo đuòng\b": "đái tháo đường",
        r"\btăng huyt áp\b": "tăng huyết áp",
        r"\btt khúc x\b": "tật khúc xạ",
        r"\bcn th\b": "cận thị",
        r"\bvin th\b": "viễn thị",
        r"\bloan th\b": "loạn thị",
        r"\bth lón hon\b": "thị lực nhỏ hơn",
        r"\bnh hon\b": "nhỏ hơn",
        r"\blón hon\b": "lớn hơn",
        r"\bnghĩa v quân s\b": "nghĩa vụ quân sự",
        r"\bquân nhân chuyên nghip\b": "quân nhân chuyên nghiệp",
        r"\bquân nhân d b\b": "quân nhân dự bị",
        r"\bnhp ngũ\b": "nhập ngũ",
        r"\bgoi nhp ngũ\b": "gọi nhập ngũ",
        r"\btuyn quân\b": "tuyển quân",
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

        # 3. Apply common legal & medical OCR dictionary corrections
        for pattern, replacement in self.TYPO_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 4. Clean up repetitive noisy scanner artifacts (e.g. "---", "___", excessive punctuation)
        text = re.sub(r"[_\-—]{4,}", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        return text.strip()
