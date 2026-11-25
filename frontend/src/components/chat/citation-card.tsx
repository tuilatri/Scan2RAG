import React from 'react';
import { FileText, AlertTriangle, Table as TableIcon, ArrowRight } from 'lucide-react';
import { Citation } from '@/types/chat';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface CitationCardProps {
  citation: Citation;
  index: number;
  isSelected?: boolean;
  onSelect: (citation: Citation) => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  citation,
  index,
  isSelected = false,
  onSelect,
}) => {
  const isSuperseded =
    citation.is_superseded === true || citation.document_id === 'thông_tư_105';

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(citation)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(citation);
        }
      }}
      className={cn(
        'group cursor-pointer rounded-lg border p-2.5 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isSelected
          ? 'border-primary bg-primary/5 shadow-sm'
          : 'border-border/70 bg-card hover:border-primary/50 hover:bg-muted/40'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
            {index + 1}
          </span>
          <span className="truncate text-xs font-medium text-foreground">
            {citation.document_name || citation.document_id || 'Tài liệu Pháp luật'}
          </span>
        </div>
        <div className="flex shrink-0 items-center space-x-1">
          {citation.is_table && (
            <Badge variant="outline" className="h-4 px-1 text-[9px] text-muted-foreground">
              <TableIcon className="h-2.5 w-2.5 mr-0.5" /> Bảng
            </Badge>
          )}
          {citation.page_number && citation.page_number > 0 && (
            <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-mono">
              Trang {citation.page_number}
            </Badge>
          )}
        </div>
      </div>

      {/* Breadcrumb path */}
      {citation.breadcrumb && (
        <p className="mt-1 line-clamp-1 text-[11px] text-muted-foreground/90 font-mono">
          {citation.breadcrumb}
        </p>
      )}

      {/* Warning for superseded legal acts */}
      {isSuperseded && (
        <div className="mt-1.5 flex items-center space-x-1 rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-700 dark:text-amber-400 border border-amber-500/20">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <span className="line-clamp-1">Quy định đã được sửa đổi/thay thế (Xem VBHN 88)</span>
        </div>
      )}

      {/* Snippet text */}
      {citation.snippet && (
        <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground/80 leading-relaxed italic">
          "{citation.snippet.replace(/\n+/g, ' ')}"
        </p>
      )}

      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground border-t pt-1.5">
        <span className="font-mono">
          {citation.rerank_score !== undefined
            ? `Độ tin cậy: ${(citation.rerank_score * 100).toFixed(0)}%`
            : 'Căn cứ trích xuất'}
        </span>
        <span className="flex items-center text-primary group-hover:translate-x-0.5 transition-transform">
          Xem văn bản gốc <ArrowRight className="h-2.5 w-2.5 ml-0.5" />
        </span>
      </div>
    </div>
  );
};
