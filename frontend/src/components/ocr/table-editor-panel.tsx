import React from 'react';
import { TableDetail } from '@/types/ocr';
import { TableCellEditor } from './table-cell-editor';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TableEditorPanelProps {
  tableDetail: TableDetail;
  editableHeaders: string[];
  editableRows: string[][];
  onUpdateCell: (rowIndex: number, colIndex: number, value: string) => void;
  onUpdateHeader?: (colIndex: number, value: string) => void;
}

export const TableEditorPanel: React.FC<TableEditorPanelProps> = ({
  tableDetail,
  editableHeaders,
  editableRows,
  onUpdateCell,
  onUpdateHeader,
}) => {
  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Title & Metadata bar */}
      <div className="border-b px-4 py-2.5 bg-card/60 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-foreground">
            {tableDetail.title || tableDetail.id}
          </h3>
          <p className="text-[11px] text-muted-foreground font-mono">
            Văn bản: {tableDetail.document_name} · Trang {tableDetail.page_number} ·{' '}
            {editableRows.length} hàng × {editableHeaders.length} cột
          </p>
        </div>
        <div className="text-[11px] text-muted-foreground italic">
          Bấm vào ô bất kỳ để sửa nội dung
        </div>
      </div>

      {/* Editable Table Grid */}
      <ScrollArea className="flex-1 p-4">
        <div className="rounded-lg border bg-card shadow-sm overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="w-10 px-2 py-2 text-[10px] font-mono text-muted-foreground text-center border-r">
                  #
                </th>
                {editableHeaders.map((header, colIdx) => (
                  <th key={colIdx} className="border-r last:border-r-0 p-1">
                    <TableCellEditor
                      value={header}
                      rowIndex={-1}
                      colIndex={colIdx}
                      isHeader={true}
                      onUpdate={(_, cIdx, val) => onUpdateHeader?.(cIdx, val)}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {editableRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="border-b last:border-b-0 hover:bg-muted/10 transition-colors"
                >
                  <td className="px-2 py-1 text-[10px] font-mono text-muted-foreground text-center border-r bg-muted/20 select-none">
                    {rowIdx + 1}
                  </td>
                  {row.map((cellValue, colIdx) => (
                    <td key={colIdx} className="border-r last:border-r-0 p-1">
                      <TableCellEditor
                        value={cellValue}
                        rowIndex={rowIdx}
                        colIndex={colIdx}
                        onUpdate={onUpdateCell}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ScrollArea>
    </div>
  );
};
