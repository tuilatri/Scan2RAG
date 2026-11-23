from app.ingestion.ocr_engine import TextBlock
from app.ingestion.table_extractor import TableExtractor


def test_format_as_markdown():
    extractor = TableExtractor()
    rows = [
        ["STT", "Bệnh tật", "Điểm 1", "Điểm 2"],
        ["1", "Cận thị dưới 1.5D", "2", "3"],
    ]
    md = extractor.format_as_markdown(rows)
    assert "| STT | Bệnh tật | Điểm 1 | Điểm 2 |" in md
    assert "| --- | --- | --- | --- |" in md
    assert "| 1 | Cận thị dưới 1.5D | 2 | 3 |" in md


def test_group_blocks_into_rows_by_y_coordinate():
    extractor = TableExtractor(y_threshold=15.0)

    # 4 blocks forming 2 rows
    # Row 1 at Y ≈ 100
    b1 = TextBlock(text="STT", confidence=0.98, box=[[10, 95], [50, 95], [50, 110], [10, 110]])
    b2 = TextBlock(
        text="Chỉ tiêu", confidence=0.97, box=[[60, 98], [150, 98], [150, 112], [60, 112]]
    )

    # Row 2 at Y ≈ 150
    b3 = TextBlock(text="1", confidence=0.99, box=[[10, 148], [50, 148], [50, 160], [10, 160]])
    b4 = TextBlock(
        text="Thị lực", confidence=0.95, box=[[60, 152], [150, 152], [150, 165], [60, 165]]
    )

    rows = extractor.group_blocks_into_rows([b4, b1, b3, b2])  # intentionally unordered input
    assert len(rows) == 2
    assert [b.text for b in rows[0]] == ["STT", "Chỉ tiêu"]
    assert [b.text for b in rows[1]] == ["1", "Thị lực"]


def test_context_header_inheritance_for_multi_page_tables():
    extractor = TableExtractor()

    # Page 2 data blocks without any header
    b1 = TextBlock(text="2", confidence=0.99, box=[[10, 50], [30, 50], [30, 65], [10, 65]])
    b2 = TextBlock(text="Viễn thị", confidence=0.95, box=[[40, 52], [120, 52], [120, 68], [40, 68]])

    inherited_header = ["STT", "Chỉ tiêu / Bệnh tật", "Điểm 1", "Điểm 2"]
    table = extractor.extract_table([b1, b2], page_number=2, context_header=inherited_header)

    assert table.header == inherited_header
    assert "| STT | Chỉ tiêu / Bệnh tật | Điểm 1 | Điểm 2 |" in table.markdown_table
    assert "| 2 | Viễn thị |" in table.markdown_table
