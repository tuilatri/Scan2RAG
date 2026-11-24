import unicodedata

from app.ingestion.text_normalizer import TextNormalizer


def test_unicode_nfc_normalization():
    normalizer = TextNormalizer()
    nfd_text = unicodedata.normalize("NFD", "Bộ Quốc phòng")
    assert unicodedata.is_normalized("NFD", nfd_text)

    normalized = normalizer.normalize(nfd_text)
    assert unicodedata.is_normalized("NFC", normalized)
    assert normalized == "Bộ Quốc phòng"


def test_legal_and_medical_typo_correction():
    normalizer = TextNormalizer()
    corrupted = "Chính ph quy đnh chc năng, nhim v, quyn hn và co cáu t chc ca B Quc phòng."
    expected = (
        "Chính phủ quy định chức năng, nhiệm vụ, quyền hạn và cơ cấu tổ chức của Bộ Quốc phòng."
    )
    assert normalizer.normalize(corrupted) == expected

    corrupted_med = "Bnh tt: Đuc thê thúy tinh, Lch th thy tinh, đái tháo đuòng và tăng huyt áp."
    expected_med = (
        "Bệnh tật: Đục thể thủy tinh, Lệch thể thủy tinh, đái tháo đường và tăng huyết áp."
    )
    assert normalizer.normalize(corrupted_med) == expected_med


def test_roman_numeral_header_preservation():
    normalizer = TextNormalizer()
    corrupted_header = "1. TIÊU CHUẨN THỂ LỰC VÀ BỆNH TẬT\nĐiều 1. Phạm vi áp dụng"
    normalized = normalizer.normalize(corrupted_header)
    assert normalized.startswith("I. TIÊU CHUẨN THỂ LỰC VÀ BỆNH TẬT")


def test_empty_or_whitespace_text():
    normalizer = TextNormalizer()
    assert normalizer.normalize("") == ""
    assert normalizer.normalize("   \n\n  ") == ""
