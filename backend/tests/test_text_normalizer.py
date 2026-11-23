import unicodedata

from app.ingestion.text_normalizer import TextNormalizer


def test_unicode_nfc_normalization():
    normalizer = TextNormalizer()
    # NFD: 'Bộ' with decomposed diacritics
    nfd_text = unicodedata.normalize("NFD", "Bộ Quốc phòng")
    assert unicodedata.is_normalized("NFD", nfd_text)

    normalized = normalizer.normalize(nfd_text)
    assert unicodedata.is_normalized("NFC", normalized)
    assert normalized == "Bộ Quốc phòng"


def test_legal_typo_correction():
    normalizer = TextNormalizer()
    corrupted = "Hà Ni, ngày 10 tháng 10. ca B trưng B Quc phòng ban hành Thng tư."
    expected = "Hà Nội, ngày 10 tháng 10. của Bộ trưởng Bộ Quốc phòng ban hành Thông tư."
    assert normalizer.normalize(corrupted) == expected


def test_roman_numeral_header_preservation():
    normalizer = TextNormalizer()
    corrupted_header = "1. TIÊU CHUẨN THỂ LỰC VÀ BỆNH TẬT\nĐiều 1. Phạm vi áp dụng"
    normalized = normalizer.normalize(corrupted_header)
    assert normalized.startswith("I. TIÊU CHUẨN THỂ LỰC VÀ BỆNH TẬT")


def test_empty_or_whitespace_text():
    normalizer = TextNormalizer()
    assert normalizer.normalize("") == ""
    assert normalizer.normalize("   \n\n  ") == ""
