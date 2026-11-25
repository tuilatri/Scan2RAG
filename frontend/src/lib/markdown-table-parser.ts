/**
 * Bi-directional parser between Markdown Table strings and 2D arrays (headers + rows).
 */

export function parseMarkdownTable(mdText: string): {
  headers: string[];
  rows: string[][];
} {
  if (!mdText || !mdText.trim()) {
    return { headers: [], rows: [] };
  }

  const lines = mdText
    .trim()
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  const tableLines = lines.filter(
    (l) => l.startsWith('|') && l.endsWith('|')
  );

  if (tableLines.length < 2) {
    return { headers: [], rows: [] };
  }

  // Header is row 0
  const headers = tableLines[0]
    .slice(1, -1)
    .split('|')
    .map((c) => c.trim());

  const rows: string[][] = [];

  for (let i = 1; i < tableLines.length; i++) {
    const line = tableLines[i];
    // Skip separator line (| --- | --- |)
    if (/^\|(\s*:?-+:?\s*\|)+$/.test(line)) {
      continue;
    }

    const cells = line
      .slice(1, -1)
      .split('|')
      .map((c) => c.trim());

    // Align with headers count
    if (cells.length < headers.length) {
      while (cells.length < headers.length) cells.push('');
    } else if (cells.length > headers.length) {
      cells.length = headers.length;
    }

    rows.push(cells);
  }

  return { headers, rows };
}

export function matrixToMarkdown(
  headers: string[],
  rows: string[][]
): string {
  if (!headers || headers.length === 0) return '';

  const headerLine = `| ${headers.join(' | ')} |`;
  const separatorLine = `| ${headers.map(() => '---').join(' | ')} |`;

  const dataLines = rows.map((row) => {
    // Pad cells if row length is shorter
    const alignedCells = headers.map((_, i) => row[i] || '');
    return `| ${alignedCells.join(' | ')} |`;
  });

  return [headerLine, separatorLine, ...dataLines].join('\n');
}
