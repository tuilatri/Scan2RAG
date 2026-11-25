import React, { useState } from 'react';
import { useOcrAudit } from '@/hooks/use-ocr-audit';
import { TableSidebar } from './table-sidebar';
import { TableEditorPanel } from './table-editor-panel';
import { TableToolbar } from './table-toolbar';
import { TableDiffViewer } from './table-diff-viewer';
import { PagePreviewCard } from './page-preview-card';
import { matrixToMarkdown } from '@/lib/markdown-table-parser';
import { CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';

export const OcrReviewContainer: React.FC = () => {
  const [viewMode, setViewMode] = useState<'grid' | 'diff' | 'raw'>('grid');

  const {
    tables,
    selectedTableId,
    tableDetail,
    editableHeaders,
    editableRows,
    isLoading,
    isSaving,
    error,
    successMessage,
    filterDocId,
    searchQuery,
    setSelectedTableId,
    setFilterDocId,
    setSearchQuery,
    updateCell,
    saveRectification,
    revertToRawBackup,
    revertToCurrentSaved,
  } = useOcrAudit();

  const currentMarkdown = matrixToMarkdown(editableHeaders, editableRows);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full overflow-hidden bg-background">
      {/* Left Sidebar: 111 tables list */}
      <TableSidebar
        tables={tables}
        selectedTableId={selectedTableId}
        filterDocId={filterDocId}
        searchQuery={searchQuery}
        onSelectTable={setSelectedTableId}
        onFilterChange={setFilterDocId}
        onSearchChange={setSearchQuery}
      />

      {/* Center & Right: Editor and PDF Preview */}
      <div className="flex flex-1 flex-col h-full overflow-hidden">
        {/* Top Action Toolbar */}
        <TableToolbar
          viewMode={viewMode}
          isSaving={isSaving}
          hasRawBackup={!!tableDetail?.raw_content_backup}
          onViewModeChange={setViewMode}
          onSave={() => saveRectification(true)}
          onRevertRaw={revertToRawBackup}
          onRevertSaved={revertToCurrentSaved}
        />

        {/* Notifications */}
        {successMessage && (
          <div className="bg-emerald-500/10 border-b border-emerald-500/20 px-4 py-1.5 text-xs text-emerald-700 dark:text-emerald-400 flex items-center">
            <CheckCircle2 className="h-3.5 w-3.5 mr-1.5 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}
        {error && (
          <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-1.5 text-xs text-destructive flex items-center">
            <AlertTriangle className="h-3.5 w-3.5 mr-1.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Main Content Body */}
        {isLoading && !tableDetail ? (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary mr-2" />
            <span className="text-xs text-muted-foreground">Đang tải bảng...</span>
          </div>
        ) : tableDetail ? (
          <div className="flex flex-1 h-full overflow-hidden">
            {/* Table Area */}
            <div className="flex-1 h-full overflow-hidden">
              {viewMode === 'grid' && (
                <TableEditorPanel
                  tableDetail={tableDetail}
                  editableHeaders={editableHeaders}
                  editableRows={editableRows}
                  onUpdateCell={updateCell}
                />
              )}
              {viewMode === 'diff' && (
                <TableDiffViewer
                  tableDetail={tableDetail}
                  currentMarkdown={currentMarkdown}
                />
              )}
              {viewMode === 'raw' && (
                <div className="flex-1 h-full p-4 overflow-auto">
                  <textarea
                    readOnly
                    value={currentMarkdown}
                    className="w-full h-full p-3 font-mono text-xs bg-muted/20 border rounded-lg resize-none focus:outline-none"
                  />
                </div>
              )}
            </div>

            {/* Right: Embedded original PDF page */}
            <PagePreviewCard
              documentId={tableDetail.document_id}
              pageNumber={tableDetail.page_number}
            />
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center text-xs text-muted-foreground">
            Vui lòng chọn một bảng từ danh mục bên trái để rà soát.
          </div>
        )}
      </div>
    </div>
  );
};
