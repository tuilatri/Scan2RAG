import React from 'react';
import { PanelLeftClose, PanelLeftOpen, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PaneToggleProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const PaneToggle: React.FC<PaneToggleProps> = ({ isOpen, onToggle }) => {
  if (!isOpen) {
    return (
      <Button variant="outline" size="sm" onClick={onToggle} className="h-8 text-xs shadow-sm">
        <FileText className="h-4 w-4 mr-1.5 text-primary" />
        Mở PDF đối soát
        <PanelLeftOpen className="h-4 w-4 ml-1.5 opacity-70" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onToggle}
      aria-label="Đóng khung PDF"
      title="Đóng khung PDF"
      className="h-7 px-2 text-xs text-muted-foreground"
    >
      <PanelLeftClose className="h-4 w-4" />
      <span className="lg:hidden ml-1.5">Đóng PDF</span>
    </Button>
  );
};
