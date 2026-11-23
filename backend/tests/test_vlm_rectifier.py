from app.ingestion.vlm_rectifier import VLMVerifier


def test_extract_numbers():
    text = "| 17 | Răng sâu: Có ≤ 3 răng sâu độ 3 | 2 | 3T | 1.5 diop |"
    nums = VLMVerifier.extract_numbers(text)
    assert "17" in nums
    assert "3" in nums
    assert "2" in nums
    assert "3T" in nums
    assert "1.5" in nums


def test_verify_numbers_preserved_pass():
    verifier = VLMVerifier()
    original = "| 1 | Cận thị 1.5 diop | 2 | 3T |"
    rectified = "| 1 | Cận thị 1.5 diop (đã hiệu chỉnh dấu) | 2 | 3T |"
    assert verifier.verify_numbers_preserved(original, rectified) is True


def test_verify_numbers_preserved_fails_on_hallucination():
    verifier = VLMVerifier()
    original = "| 1 | Cận thị 1.5 diop | Điểm 2 | Điểm 6 |"
    # LLM hallucinates and changes 1.5 to 2.5 and forgets 6
    hallucinated = "| 1 | Cận thị 2.5 diop | Điểm 2 | Điểm 5 |"
    assert verifier.verify_numbers_preserved(original, hallucinated) is False


def test_clean_markdown_response():
    raw_response = (
        "Dưới đây là bảng đã sửa dấu:\n\n"
        "```markdown\n"
        "| STT | Bệnh tật | Điểm |\n"
        "| --- | --- | --- |\n"
        "| 1 | Cận thị | 2 |\n"
        "```\n\n"
        "Chúc bạn một ngày tốt lành!"
    )
    cleaned = VLMVerifier.clean_markdown_response(raw_response)
    assert cleaned.startswith("| STT | Bệnh tật | Điểm |")
    assert cleaned.endswith("| 1 | Cận thị | 2 |")
    assert "Chúc bạn một ngày" not in cleaned
