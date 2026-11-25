import React from 'react';
import { RotateCcw, CheckCircle, Code2, Table as TableIcon, Eye, Undo2, Redo2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TableToolbarProps {
  viewMode: 'grid' | 'diff' | 'raw';
  isSaving: boolean;
  hasRawBackup: boolean;
  canUndo?: boolean;
  canRedo?: boolean;
  onViewModeChange: (mode: 'grid' | 'diff' | 'raw') => void;
  onSave: () => void;
  onRevertRaw: () => void;
  onRevertSaved: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
}

export const TableToolbar: React.FC<TableToolbarProps> = ({
  viewMode,
  isSaving,
  hasRawBackup,
  canUndo = false,
  canRedo = false,
  onViewModeChange,
  onSave,
  onRevertRaw,
  onRevertSaved,
  onUndo,
  onRedo,
}) => {
  return (
    <div className="flex items-center justify-between border-b bg-card px-4 py-2 text-xs">
      {/* Mode Switcher */}
      <div className="flex items-center space-x-1 bg-muted p-0.5 rounded-lg border">
        <Button
          variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={() => onViewModeChange('grid')}
        >
          <TableIcon className="h-3.5 w-3.5 mr-1" />
          <span>Bảng Lưới</span>
        </Button>
        <Button
          variant={viewMode === 'diff' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={() => onViewModeChange('diff')}
        >
          <Eye className="h-3.5 w-3.5 mr-1" />
          <span>So sánh Diff</span>
        </Button>
        <Button
          variant={viewMode === 'raw' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={() => onViewModeChange('raw')}
        >
          <Code2 className="h-3.5 w-3.5 mr-1" />
          <span>Mã Markdown</span>
        </Button>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-2">
        {onUndo && (
          <Button
            variant="ghost"
            size="sm"
            disabled={!canUndo}
            className="h-7 px-2 text-xs"
            onClick={onUndo}
            title="Hoàn tác (Undo)"
          >
            <Undo2 className="h-3.5 w-3.5" />
          </Button>
        )}
        {onRedo && (
          <Button
            variant="ghost"
            size="sm"
            disabled={!canRedo}
            className="h-7 px-2 text-xs"
            onClick={onRedo}
            title="Làm lại (Redo)"
          >
            <Redo2 className="h-3.5 w-3.5" />
          </Button>
        )}
        {hasRawBackup && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground"
            onClick={onRevertRaw}
            title="Khôi phục lại bản quét OCR gốc"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1" />
            <span>Khôi phục OCR gốc</span>
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          className="h-7 px-2.5 text-xs"
          onClick={onRevertSaved}
          title="Hủy các ô vừa sửa chưa lưu"
        >
          <span>Khôi phục đã lưu</span>
        </Button>
        <Button
          size="sm"
          disabled={isSaving}
          className="h-7 px-3 text-xs"
          onClick={onSave}
        >
          <CheckCircle className="h-3.5 w-3.5 mr-1" />
          <span>{isSaving ? 'Đang lưu...' : 'Lưu & Phê duyệt'}</span>
        </Button>
      </div>
    </div>
  );
};
