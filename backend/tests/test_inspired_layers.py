from app.ingestion.ocr_pipeline import OCRPipeline
from app.ingestion.table_structure import extract_score_rows
from app.ingestion.vietnamese_corrector import correct


def test_table_structure_uses_score_header_and_skips_header_row():
    table = (
        "| TT | Bệnh tật | Điểm |\n"
        "| --- | --- | --- |\n"
        "| 4 | Loạn thị: |  |\n"
        "|  | - Cận thị từ - 3D đến dưới - 4D | 4 |\n"
    )
    assert extract_score_rows(table) == [("- Cận thị từ - 3D đến dưới - 4D", 4)]


def test_corrector_fixes_noise_without_touching_numbers():
    result = correct("Cận thềE từ - 3D đến dưới - 4D cho 4 điểm")
    assert "Cận thị" in result
    assert "- 3D" in result
    assert "4 điểm" in result


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
