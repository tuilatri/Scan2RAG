import React from 'react';
import { ZoomIn, ZoomOut, RotateCcw, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PdfToolbarProps {
  currentPage: number;
  totalPages?: number;
  zoomLevel: number;
  pdfUrl: string;
  onPageChange: (page: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

export const PdfToolbar: React.FC<PdfToolbarProps> = ({
  currentPage,
  totalPages = 120,
  zoomLevel,
  pdfUrl,
  onPageChange,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}) => {
  return (
    <div className="flex items-center justify-between border-b bg-card/80 px-3 py-1.5 text-xs backdrop-blur">
      {/* Page Navigation */}
      <div className="flex items-center space-x-1">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          title="Trang trước"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center space-x-1 font-mono text-xs text-muted-foreground px-1">
          <span className="font-semibold text-foreground">{currentPage}</span>
          <span>/</span>
          <span>{totalPages}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          title="Trang sau"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Zoom Controls */}
      <div className="flex items-center space-x-1">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={onZoomOut}
          title="Thu nhỏ"
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </Button>
        <span className="font-mono text-[11px] text-muted-foreground min-w-[36px] text-center">
          {zoomLevel}%
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={onZoomIn}
          title="Phóng to"
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 text-muted-foreground"
          onClick={onResetZoom}
          title="Mặc định"
        >
          <RotateCcw className="h-3 w-3" />
        </Button>
      </div>

      {/* External Open */}
      <div className="flex items-center">
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center space-x-1 rounded px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Mở toàn màn hình trong tab mới"
        >
          <span>Mở tab mới</span>
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
};
