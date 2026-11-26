import React from 'react';
import { TableSummary } from '@/types/ocr';
import { TableSidebarItem } from './table-sidebar-item';
import { ThinScrollArea } from '@/components/ui/thin-scroll-area';
import { Input } from '@/components/ui/input';
import { Search, Filter } from 'lucide-react';

interface TableSidebarProps {
  tables: TableSummary[];
  selectedTableId: string | null;
  filterDocId: string;
  searchQuery: string;
  onSelectTable: (id: string) => void;
  onFilterChange: (docId: string) => void;
  onSearchChange: (query: string) => void;
}

const DOCUMENT_OPTIONS = [
  { id: 'all', label: 'Tất cả văn bản' },
  { id: 'thông_tư_88', label: 'Thông tư 88 (50 bảng)' },
  { id: 'thông_tư_105', label: 'Thông tư 105 (45 bảng)' },
  { id: 'thông_tư_106', label: 'Thông tư 106 (16 bảng)' },
];

export const TableSidebar: React.FC<TableSidebarProps> = ({
  tables,
  selectedTableId,
  filterDocId,
  searchQuery,
  onSelectTable,
  onFilterChange,
  onSearchChange,
}) => {
  return (
    <div className="flex h-full w-80 flex-col border-r bg-card/60">
      {/* Header & Search */}
      <div className="p-3 border-b space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground tracking-tight">
            Danh mục Bảng Y tế
          </span>
          <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {tables.length} bảng
          </span>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Tìm theo tên bệnh tật, bảng..."
            className="h-8 pl-8 text-xs bg-background"
          />
        </div>

        {/* Filter dropdown / select */}
        <div className="flex items-center space-x-1">
          <Filter className="h-3 w-3 text-muted-foreground" />
          <select
            value={filterDocId}
            onChange={(e) => onFilterChange(e.target.value)}
            className="w-full text-xs bg-transparent border rounded h-7 px-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {DOCUMENT_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id} className="bg-popover text-popover-foreground">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tables List */}
      <ThinScrollArea orientation="vertical" className="min-h-0 flex-1" viewportClassName="p-2">
        {tables.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted-foreground">
            Không tìm thấy bảng phù hợp.
          </div>
        ) : (
          <div className="space-y-1.5">
            {tables.map((table) => (
              <TableSidebarItem
                key={table.id}
                table={table}
                isSelected={selectedTableId === table.id}
                onSelect={onSelectTable}
              />
            ))}
          </div>
        )}
      </ThinScrollArea>
    </div>
  );
};
