import { describe, it, expect } from 'vitest';
import { parseMarkdownTable, matrixToMarkdown } from '@/lib/markdown-table-parser';

describe('Markdown Table Bi-directional Parser', () => {
  const sampleMarkdown = `| TT | Bệnh tật | Điểm |
| --- | --- | --- |
| 1 | Cận thị dưới -3D | Cho điểm theo mục 1.2 |
| 2 | Cận thị từ -3D đến dưới -4D | 4 |
| 3 | Cận thị từ -4D đến dưới -5D | 5 |`;

  it('parses markdown table into headers and rows matrix', () => {
    const { headers, rows } = parseMarkdownTable(sampleMarkdown);
    expect(headers).toEqual(['TT', 'Bệnh tật', 'Điểm']);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toEqual(['1', 'Cận thị dưới -3D', 'Cho điểm theo mục 1.2']);
    expect(rows[1][2]).toBe('4');
  });

  it('converts matrix back to valid markdown table', () => {
    const headers = ['Mã', 'Tên'];
    const rows = [
      ['01', 'Mắt'],
      ['02', 'Tai mũi họng'],
    ];
    const generatedMd = matrixToMarkdown(headers, rows);
    expect(generatedMd).toContain('| Mã | Tên |');
    expect(generatedMd).toContain('| --- | --- |');
    expect(generatedMd).toContain('| 01 | Mắt |');
  });

  it('handles empty input gracefully', () => {
    const { headers, rows } = parseMarkdownTable('');
    expect(headers).toEqual([]);
    expect(rows).toEqual([]);
  });
});
