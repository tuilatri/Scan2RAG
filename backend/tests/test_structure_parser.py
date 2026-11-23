"""Unit tests for LegalStructureParser."""

from app.ingestion.structure_parser import LegalStructureParser
from app.models.document_schema import HierarchyLevel


def test_legal_structure_parser():
    sample_text = [
        "THÔNG TƯ 105/2023/TT-BQP",
        "Chương I. QUY ĐỊNH CHUNG",
        "Điều 1. Phạm vi điều chỉnh",
        "1. Thông tư này quy định về tiêu chuẩn sức khỏe.",
        "a) Khám sức khỏe thực hiện nghĩa vụ quân sự;",
        "b) Giám định sức khỏe quân sự.",
        "2. Áp dụng đối với công dân Việt Nam.",
        "Điều 2. Đối tượng áp dụng",
        "Công dân trong độ tuổi gọi nhập ngũ.",
    ]

    parser = LegalStructureParser(
        document_id="tt_105_2023", document_name="Thông tư 105/2023/TT-BQP"
    )
    nodes = parser.parse_lines(sample_text, page_number=1)

    assert len(nodes) > 0

    chapters = [n for n in nodes if n.level == HierarchyLevel.CHAPTER]
    articles = [n for n in nodes if n.level == HierarchyLevel.ARTICLE]
    clauses = [n for n in nodes if n.level == HierarchyLevel.CLAUSE]
    points = [n for n in nodes if n.level == HierarchyLevel.POINT]

    assert len(chapters) == 1
    assert chapters[0].title.startswith("Chương I")

    assert len(articles) == 2
    assert articles[0].title == "Điều 1"
    assert articles[0].parent_id == chapters[0].id

    assert len(clauses) == 2
    assert clauses[0].title == "Khoản 1"
    assert clauses[0].parent_id == articles[0].id

    assert len(points) == 2
    assert points[0].title == "Điểm a"
    assert points[0].parent_id == clauses[0].id
