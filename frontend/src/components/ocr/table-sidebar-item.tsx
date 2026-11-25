import React from 'react';
import { TableSummary } from '@/types/ocr';
import { Badge } from '@/components/ui/badge';
import { Table as TableIcon, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TableSidebarItemProps {
  table: TableSummary;
  isSelected: boolean;
  onSelect: (tableId: string) => void;
}

export const TableSidebarItem: React.FC<TableSidebarItemProps> = ({
  table,
  isSelected,
  onSelect,
}) => {
  return (
    <div
      onClick={() => onSelect(table.id)}
      className={cn(
        'group cursor-pointer rounded-lg border p-2 text-left transition-all duration-150',
        isSelected
          ? 'border-primary bg-primary/5 shadow-sm'
          : 'border-border/60 bg-card hover:border-primary/40 hover:bg-muted/30'
      )}
    >
      <div className="flex items-start justify-between gap-1.5">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          <TableIcon className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span className="truncate text-xs font-medium text-foreground">
            {table.title || table.id}
          </span>
        </div>
        <Badge variant="secondary" className="h-4 px-1 text-[9px] font-mono shrink-0">
          Trang {table.page_number}
        </Badge>
      </div>

      <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
        <span className="font-mono">
          {table.rows_count} hàng × {table.cols_count} cột
        </span>
        <div>
          {table.hitl_approved ? (
            <span className="inline-flex items-center text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" /> Đã duyệt
            </span>
          ) : table.vlm_rectified ? (
            <span className="inline-flex items-center text-blue-600 dark:text-blue-400">
              VLM nắn chỉnh
            </span>
          ) : (
            <span className="inline-flex items-center text-amber-600 dark:text-amber-400">
              <AlertCircle className="h-2.5 w-2.5 mr-0.5" /> Chờ rà soát
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
