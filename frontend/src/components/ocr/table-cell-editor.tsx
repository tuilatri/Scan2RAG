import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface TableCellEditorProps {
  value: string;
  rowIndex: number;
  colIndex: number;
  isHeader?: boolean;
  onUpdate: (rowIndex: number, colIndex: number, newValue: string) => void;
}

export const TableCellEditor: React.FC<TableCellEditorProps> = React.memo(
  ({ value, rowIndex, colIndex, isHeader = false, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [localValue, setLocalValue] = useState(value);

    useEffect(() => {
      setLocalValue(value);
    }, [value]);

    const handleBlur = () => {
      setIsEditing(false);
      if (localValue !== value) {
        onUpdate(rowIndex, colIndex, localValue);
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        handleBlur();
      } else if (e.key === 'Escape') {
        setLocalValue(value);
        setIsEditing(false);
      }
    };

    // Sub-header row detection (row where subsequent cells are empty)
    const isSubHeader = !isHeader && colIndex === 0 && (/^\d+(\.\d+)?\./.test(value) || value.includes('TIÊU CHUẨN'));

    // Military Medical Score Validation (1 to 6)
    const isScoreCol = !isHeader && (colIndex === 2 || colIndex === 3 || colIndex === 4);
    const numVal = parseInt(value.trim(), 10);
    const isInvalidScore = isScoreCol && value.trim() && !isNaN(numVal) && (numVal < 1 || numVal > 6);

    if (isEditing) {
      return (
        <input
          autoFocus
          type="text"
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          className="w-full bg-background border border-primary px-2 py-1 text-xs focus:outline-none rounded"
        />
      );
    }

    return (
      <div
        onClick={() => setIsEditing(true)}
        className={cn(
          'min-h-[28px] px-2.5 py-1 text-xs cursor-text rounded transition-colors break-words',
          isHeader ? 'font-semibold text-foreground bg-muted/40' : 'hover:bg-muted/30 text-foreground',
          isSubHeader && 'font-semibold text-primary/90 bg-primary/5',
          isInvalidScore && 'bg-destructive/15 text-destructive border border-destructive/30 font-bold'
        )}
        title="Bấm để chỉnh sửa ô"
      >
        {value || <span className="text-muted-foreground/40 italic">--</span>}
      </div>
    );
  }
);
