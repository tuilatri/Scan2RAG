from app.ingestion.vlm_rectifier import VLMVerifier


def test_extract_numbers():
    text = "| 17 | Răng sâu: Có ≤ 3 răng sâu độ 3 | 2 | 3T | 1.5 diop | Sức nhai 85% |"
    nums = VLMVerifier.extract_numbers(text)
    assert "17" in nums
    assert "3" in nums
    assert "2" in nums
    assert "3T" in nums
    assert "1.5" in nums
    assert "85%" in nums


def test_verify_numbers_preserved_exact_match():
    verifier = VLMVerifier()
    original = "| 1 | Cận thị 1.5 diop | 2 | 3T | 85% |"
    rectified = "| 1 | Cận thị 1.5 diop (đã hiệu chỉnh dấu) | 2 | 3T | 85% |"
    is_valid, error = verifier.verify_numbers_preserved(original, rectified)
    assert is_valid is True
    assert error is None


def test_verify_numbers_preserved_fails_on_losing_single_number_in_many():
    verifier = VLMVerifier()
    # 48 numbers represented as a sequence
    original_numbers = [str(i) for i in range(1, 49)] + ["5T"]
    original_text = " ".join(original_numbers)

    # Rectified text loses just ONE number: '5T'
    rectified_numbers = [str(i) for i in range(1, 49)]
    rectified_text = " ".join(rectified_numbers)

    is_valid, error = verifier.verify_numbers_preserved(original_text, rectified_text)
    assert is_valid is False
    assert "5T" in error


def test_verify_numbers_preserved_fails_on_duplicate_loss():
    verifier = VLMVerifier()
    # Original has three 2s and two 3s
    original = "| 1 | Bệnh A | 2 | 2 | 2 | 3 | 3 |"
    # Rectified loses one of the 2s
    rectified = "| 1 | Bệnh A | 2 | 2 | 3 | 3 |"

    is_valid, error = verifier.verify_numbers_preserved(original, rectified)
    assert is_valid is False
    assert "2 (mất 1)" in error


def test_verify_numbers_preserved_fails_on_hallucinated_added_number():
    verifier = VLMVerifier()
    original = "| 1 | Cận thị | 2 |"
    # LLM hallucinates an extra number 30
    rectified = "| 1 | Cận thị | 2 | 30 |"

    is_valid, error = verifier.verify_numbers_preserved(original, rectified)
    assert is_valid is False
    assert "30 (thêm 1)" in error


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
