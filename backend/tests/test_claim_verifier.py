from app.grounding.claim_verifier import verify_claims


def test_pass_when_all_required_claims_present():
    result = verify_claims(
        "Không gọi nhập ngũ vì viễn thị các mức độ.",
        ["không gọi nhập ngũ", "viễn thị các mức độ"],
    )
    assert result == {"passed": True, "checked": 2, "missing": []}


def test_reports_missing_claims():
    result = verify_claims(
        "Cần xem xét thêm.",
        ["không gọi nhập ngũ", "viễn thị các mức độ"],
    )
    assert result["passed"] is False
    assert result["missing"] == ["không gọi nhập ngũ", "viễn thị các mức độ"]


def test_empty_requirements_always_pass():
    assert verify_claims("", [])["passed"] is True
