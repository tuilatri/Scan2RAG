import { useState, useEffect, useCallback, useRef } from 'react';
import { TableSummary, TableDetail } from '@/types/ocr';
import { matrixToMarkdown, parseMarkdownTable } from '@/lib/markdown-table-parser';

interface UseOcrAuditOptions {
  apiBaseUrl?: string;
}

export function useOcrAudit({
  apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
}: UseOcrAuditOptions = {}) {
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [tableDetail, setTableDetail] = useState<TableDetail | null>(null);
  const [editableRows, setEditableRows] = useState<string[][]>([]);
  const [editableHeaders, setEditableHeaders] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [filterDocId, setFilterDocId] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const detailAbortRef = useRef<AbortController | null>(null);

  // Fetch list of tables
  const fetchTables = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/ocr/tables`);
      if (!res.ok) throw new Error(`Lỗi tải danh mục bảng: ${res.statusText}`);
      const data: TableSummary[] = await res.json();
      setTables(data);
      if (data.length > 0 && !selectedTableId) {
        setSelectedTableId(data[0].id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Không thể kết nối API bảng OCR.');
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, selectedTableId]);

  // Fetch detail when selectedTableId changes (with AbortController to prevent stale race)
  const fetchTableDetail = useCallback(
    async (tableId: string) => {
      if (detailAbortRef.current) {
        detailAbortRef.current.abort();
      }
      const controller = new AbortController();
      detailAbortRef.current = controller;

      setIsLoading(true);
      setError(null);
      setSuccessMessage(null);
      try {
        const res = await fetch(`${apiBaseUrl}/api/v1/ocr/tables/${tableId}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`Lỗi tải chi tiết bảng: ${res.statusText}`);
        const data: TableDetail = await res.json();
        setTableDetail(data);
        setEditableHeaders([...data.headers]);
        setEditableRows(data.rows.map((r) => [...r]));
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setError(err instanceof Error ? err.message : 'Lỗi tải dữ liệu bảng.');
      } finally {
        if (detailAbortRef.current === controller) {
          setIsLoading(false);
        }
      }
    },
    [apiBaseUrl]
  );

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  useEffect(() => {
    if (selectedTableId) {
      fetchTableDetail(selectedTableId);
    }
  }, [selectedTableId, fetchTableDetail]);

  // Update a single cell
  const updateCell = useCallback((rowIndex: number, colIndex: number, value: string) => {
    setEditableRows((prev) => {
      const updated = prev.map((row, rIdx) => {
        if (rIdx === rowIndex) {
          const newRow = [...row];
          newRow[colIndex] = value;
          return newRow;
        }
        return row;
      });
      return updated;
    });
  }, []);

  // Save changes
  const saveRectification = useCallback(
    async (approved = true, reviewerNotes?: string) => {
      if (!selectedTableId) return;

      setIsSaving(true);
      setError(null);
      setSuccessMessage(null);

      const newMarkdown = matrixToMarkdown(editableHeaders, editableRows);

      try {
        const res = await fetch(
          `${apiBaseUrl}/api/v1/ocr/tables/${selectedTableId}/rectify`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              content: newMarkdown,
              approved,
              reviewer_notes: reviewerNotes,
            }),
          }
        );

        if (!res.ok) {
          const errorData = await res.json().catch(() => null);
          throw new Error(errorData?.detail || 'Lưu bảng thất bại.');
        }

        setSuccessMessage('Đã lưu và phê duyệt bảng thành công!');
        // Refresh detail and tables list
        await fetchTables();
        if (tableDetail) {
          setTableDetail((prev) =>
            prev
              ? {
                  ...prev,
                  content: newMarkdown,
                  headers: editableHeaders,
                  rows: editableRows,
                }
              : null
          );
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Lỗi khi lưu bảng.');
      } finally {
        setIsSaving(false);
      }
    },
    [apiBaseUrl, selectedTableId, editableHeaders, editableRows, fetchTables, tableDetail]
  );

  // Revert to raw OCR backup or current saved
  const revertToRawBackup = useCallback(() => {
    if (!tableDetail?.raw_content_backup) return;
    const { headers, rows } = parseMarkdownTable(tableDetail.raw_content_backup);
    setEditableHeaders(headers);
    setEditableRows(rows);
    setSuccessMessage('Đã khôi phục về bản quét OCR thô ban đầu.');
  }, [tableDetail]);

  const revertToCurrentSaved = useCallback(() => {
    if (!tableDetail) return;
    setEditableHeaders([...tableDetail.headers]);
    setEditableRows(tableDetail.rows.map((r) => [...r]));
    setSuccessMessage('Đã khôi phục về bản đã lưu gần nhất.');
  }, [tableDetail]);

  // Filtered tables list
  const filteredTables = tables.filter((t) => {
    const matchesDoc = filterDocId === 'all' || t.document_id === filterDocId;
    const matchesQuery =
      !searchQuery.trim() ||
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesDoc && matchesQuery;
  });

  return {
    tables: filteredTables,
    allTablesCount: tables.length,
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
    refreshTables: fetchTables,
  };
}
