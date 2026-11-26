import React from 'react';
import { cn } from '@/lib/utils';
import { PaneToggle } from './pane-toggle';

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
          'flex flex-col h-full',
          isRightPaneOpen ? 'w-full lg:w-[50%] xl:w-[48%]' : 'w-full'
        )}
      >
        {leftPane}
      </div>

      {/* Toggle Button when Pane is Closed */}
      {!isRightPaneOpen && (
        <div className="absolute right-4 top-4 z-30">
          <PaneToggle isOpen={false} onToggle={onToggleRightPane} />
        </div>
      )}

      {/* Right Synchronized PDF Pane (Desktop side-by-side + Mobile full-screen overlay) */}
      {isRightPaneOpen && (
        <div className="fixed inset-0 z-40 flex flex-col bg-background lg:static lg:z-auto lg:flex-1">
          <div className="flex h-9 shrink-0 items-center justify-end border-b px-2">
            <PaneToggle isOpen onToggle={onToggleRightPane} />
          </div>
          <div className="min-h-0 flex-1">{rightPane}</div>
        </div>
      )}
    </div>
  );
};
