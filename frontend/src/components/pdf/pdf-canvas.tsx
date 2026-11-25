import React, { useState } from 'react';
import { Citation } from '@/types/chat';
import { FileText, ExternalLink, Table as TableIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PdfCanvasProps {
  docId: string;
  page: number;
  pdfUrl: string;
  zoomLevel: number;
  activeCitation?: Citation | null;
}

export const PdfCanvas: React.FC<PdfCanvasProps> = ({
  docId,
  page,
  pdfUrl,
  zoomLevel,
  activeCitation,
}) => {
  const [embedError, setEmbedError] = useState(false);

  // Construct iframe/embed URL with page anchor
  const viewerUrl = `${pdfUrl}#page=${page}&zoom=${zoomLevel}`;

  return (
    <div className="relative flex-1 h-full w-full bg-muted/20 overflow-hidden flex flex-col">
      {/* Active Snippet / Table Highlight Banner */}
      {activeCitation && (
        <div className="border-b bg-primary/5 px-3 py-2 text-xs">
          <div className="flex items-center justify-between text-[11px] font-medium text-primary">
            <span className="flex items-center">
              {activeCitation.is_table ? (
                <TableIcon className="h-3 w-3 mr-1" />
              ) : (
                <FileText className="h-3 w-3 mr-1" />
              )}
              {activeCitation.breadcrumb || 'Đoạn trích đối chiếu'}
            </span>
            <span className="font-mono text-muted-foreground text-[10px]">
              Trang {activeCitation.page_number}
            </span>
          </div>
          {activeCitation.snippet && (
            <p className="mt-1 max-h-16 overflow-y-auto text-[11px] text-foreground/90 font-mono bg-card p-1.5 rounded border leading-relaxed">
              {activeCitation.snippet}
            </p>
          )}
        </div>
      )}

      {/* Main PDF Viewer (native modern browser PDF object) */}
      {!embedError ? (
        <iframe
          key={`${docId}-${page}-${zoomLevel}`}
          src={viewerUrl}
          title={`PDF Viewer - ${docId} (Trang ${page})`}
          className="h-full w-full border-0"
          onError={() => setEmbedError(true)}
        />
      ) : (
        <div className="flex flex-col items-center justify-center h-full p-6 text-center">
          <FileText className="h-10 w-10 text-muted-foreground mb-2" />
          <p className="text-xs text-muted-foreground max-w-xs">
            Trình duyệt không hỗ trợ xem trước PDF dạng nhúng trực tiếp.
          </p>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center space-x-1.5"
          >
            <Button size="sm" variant="outline" className="text-xs">
              <span>Mở tệp PDF trong tab mới</span>
              <ExternalLink className="h-3 w-3 ml-1" />
            </Button>
          </a>
        </div>
      )}
    </div>
  );
};
