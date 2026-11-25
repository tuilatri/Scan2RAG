import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { PanelLeftClose, PanelLeftOpen, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SplitPaneProps {
  leftPane: React.ReactNode;
  rightPane: React.ReactNode;
  isRightPaneOpen: boolean;
  onToggleRightPane: () => void;
  activeDocName?: string;
}

export const SplitPane: React.FC<SplitPaneProps> = ({
  leftPane,
  rightPane,
  isRightPaneOpen,
  onToggleRightPane,
  activeDocName,
}) => {
  return (
    <div className="relative flex h-[calc(100vh-3.5rem)] w-full overflow-hidden bg-background">
      {/* Left Chat Pane */}
      <div
        className={cn(
          'flex flex-col h-full transition-all duration-200 ease-in-out',
          isRightPaneOpen ? 'w-full lg:w-[50%] xl:w-[48%]' : 'w-full'
        )}
      >
        {leftPane}
      </div>

      {/* Toggle Button when Pane is Closed */}
      {!isRightPaneOpen && (
        <div className="absolute right-4 top-4 z-30">
          <Button
            variant="outline"
            size="sm"
            onClick={onToggleRightPane}
            className="shadow-sm bg-background/90 backdrop-blur text-xs"
          >
            <FileText className="h-3.5 w-3.5 mr-1.5 text-primary" />
            <span>Mở PDF đối soát</span>
            <PanelLeftOpen className="h-3.5 w-3.5 ml-1.5 opacity-70" />
          </Button>
        </div>
      )}

      {/* Right Synchronized PDF Pane (Desktop side-by-side + Mobile full-screen overlay) */}
      {isRightPaneOpen && (
        <div className="fixed inset-0 z-40 flex flex-col bg-background lg:static lg:z-auto lg:flex-1 transition-all duration-200 ease-in-out">
          <div className="absolute right-2 top-2 z-50">
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleRightPane}
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground bg-background/90 backdrop-blur"
              title="Đóng khung PDF"
            >
              <PanelLeftClose className="h-4 w-4 lg:mr-0 mr-1" />
              <span className="lg:hidden">Đóng PDF</span>
            </Button>
          </div>
          {rightPane}
        </div>
      )}
    </div>
  );
};
