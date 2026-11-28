from app.ingestion.ocr_pipeline import OCRPipeline
from app.ingestion.table_structure import extract_score_rows, extract_score_rows_from_text
from app.ingestion.vietnamese_corrector import correct


def test_table_structure_uses_score_header_and_skips_header_row():
    table = (
        "| TT | Bệnh tật | Điểm |\n"
        "| --- | --- | --- |\n"
        "| 4 | Loạn thị: |  |\n"
        "|  | - Cận thị từ - 3D đến dưới - 4D | 4 |\n"
    )
    assert extract_score_rows(table) == [("- Cận thị từ - 3D đến dưới - 4D", 4)]
    assert extract_score_rows(
        "| TT | Bệnh tật | Đim |\n|  | - Viễn thị +3D đến +4D | 5 |"
    ) == [("- Viễn thị +3D đến +4D", 5)]


def test_corrector_fixes_noise_without_touching_numbers():
    result = correct("Cận thềE từ - 3D đến dưới - 4D cho 4 điểm")
    assert "Cận thị" in result
    assert "- 3D" in result
    assert "4 điểm" in result


def test_corrector_uses_curated_domain_dictionary():
    assert correct("Bnh tt").lower() == "bệnh tật"
    assert correct("Đim").lower() == "điểm"


def test_plain_text_score_rows_attach_standalone_score():
    text = "- Cận thị từ - 3D đến dưới - 4D\n4\n- Viễn thị +3D đến +4D\n5\n"
    assert extract_score_rows_from_text(text) == [
        ("- Cận thị từ - 3D đến dưới - 4D", 4),
        ("- Viễn thị +3D đến +4D", 5),
    ]


def test_corrector_restores_three_protected_phrases():
    assert correct("có sc khe loi 1,\nloi 2, loi 3 theo") == (
        "có sức khỏe loại 1, loại 2, loại 3 theo"
    )
    assert correct("viễn thị các mức đ;") == "viễn thị các mức độ;"
    assert correct("viễn thị các mục đ;") == "viễn thị các mức độ;"
    assert correct("không cho điểm đ phân loi sc khe.") == (
        "không cho điểm để phân loại sức khỏe."
    )
    assert correct("không cho điểm đ phân loi sức khỏe.") == (
        "không cho điểm để phân loại sức khỏe."
    )


def test_corrector_preserves_many_numbers_without_placeholder_collision():
    text = "Thông tư 105/2023/TT-BQP trang 105 và 10"
    assert correct(text) == text


def test_corrector_preserves_protected_legal_phrase():
    text = "Không gọi nhập ngũ đối với viễn thị các mức độ"
    assert correct(text) == text


def test_ocr_pipeline_uses_injected_layers_in_order():
    calls = []

    def preprocess(image):
        calls.append("pre")
        return image + "-clean"

    def recognize(image):
        calls.append("ocr")
        return "| TT | Điểm |\n|  | 4 |"

    def fix(text):
        calls.append("correct")
        return text

    def structure(text):
        calls.append("structure")
        return [("x", 4)]

    pipeline = OCRPipeline(preprocess, recognize, fix, structure)
    result = pipeline.run("img")
    assert calls == ["pre", "ocr", "correct", "structure"]
    assert result["score_rows"] == [("x", 4)]
