import React from 'react';
import { TableDetail } from '@/types/ocr';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TableDiffViewerProps {
  tableDetail: TableDetail;
  currentMarkdown: string;
}

export const TableDiffViewer: React.FC<TableDiffViewerProps> = ({
  tableDetail,
  currentMarkdown,
}) => {
  const rawBackup = tableDetail.raw_content_backup || tableDetail.content;

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden p-4">
      <div className="grid grid-cols-2 gap-4 h-full">
        {/* Left: Raw OCR */}
        <div className="flex flex-col h-full border rounded-lg bg-card overflow-hidden">
          <div className="border-b bg-muted/40 px-3 py-2 text-xs font-semibold text-muted-foreground">
            Bản quét OCR Thô (PaddleOCR trước nắn chỉnh)
          </div>
          <ScrollArea className="flex-1 p-3">
            <pre className="text-xs font-mono whitespace-pre-wrap text-foreground/80 leading-relaxed">
              {rawBackup}
            </pre>
          </ScrollArea>
        </div>

        {/* Right: Current VLM / Rectified */}
        <div className="flex flex-col h-full border rounded-lg bg-card overflow-hidden">
          <div className="border-b bg-primary/10 px-3 py-2 text-xs font-semibold text-primary">
            Bản đã Nắn chỉnh (VLM Rectified / Con người duyệt)
          </div>
          <ScrollArea className="flex-1 p-3">
            <pre className="text-xs font-mono whitespace-pre-wrap text-foreground leading-relaxed">
              {currentMarkdown}
            </pre>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
};
