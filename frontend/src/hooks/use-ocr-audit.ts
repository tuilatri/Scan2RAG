import { useState, useEffect, useCallback, useRef } from 'react';
import { TableSummary, TableDetail } from '@/types/ocr';
import { matrixToMarkdown, parseMarkdownTable } from '@/lib/markdown-table-parser';
import { API_BASE_URL, apiHeaders } from '@/lib/api-config';

interface UseOcrAuditOptions {
  apiBaseUrl?: string;
}

export function useOcrAudit({
  apiBaseUrl = API_BASE_URL,
}: UseOcrAuditOptions = {}) {
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [tableDetail, setTableDetail] = useState<TableDetail | null>(null);
  const [editableRows, setEditableRows] = useState<string[][]>([]);
  const [editableHeaders, setEditableHeaders] = useState<string[]>([]);
  const [history, setHistory] = useState<{ headers: string[]; rows: string[][] }[]>([]);
  const [historyIdx, setHistoryIdx] = useState<number>(-1);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [filterDocId, setFilterDocId] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const detailAbortRef = useRef<AbortController | null>(null);
  const tablesAbortRef = useRef<AbortController | null>(null);

  // Fetch list of tables; abort any superseded request to avoid stale writes.
  const fetchTables = useCallback(async () => {
    tablesAbortRef.current?.abort();
    const controller = new AbortController();
    tablesAbortRef.current = controller;

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/ocr/tables`, {
        headers: apiHeaders(),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Lỗi tải danh mục bảng: ${res.statusText}`);
      const data: TableSummary[] = await res.json();
      if (controller.signal.aborted) return;
      setTables(data);
      setSelectedTableId((current) => current ?? data[0]?.id ?? null);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'Không thể kết nối API bảng OCR.');
    } finally {
      if (tablesAbortRef.current === controller) {
        setIsLoading(false);
      }
    }
  }, [apiBaseUrl]);

  useEffect(() => () => tablesAbortRef.current?.abort(), []);

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
          headers: apiHeaders(),
        });
        if (!res.ok) throw new Error(`Lỗi tải chi tiết bảng: ${res.statusText}`);
        const data: TableDetail = await res.json();
        setTableDetail(data);
        setEditableHeaders([...data.headers]);
        setEditableRows(data.rows.map((r) => [...r]));
        setHistory([{ headers: [...data.headers], rows: data.rows.map((r) => [...r]) }]);
        setHistoryIdx(0);
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

  const pushHistory = useCallback(
    (nextHeaders: string[], nextRows: string[][]) => {
      setHistory((prev) => [
        ...prev.slice(0, historyIdx + 1),
        { headers: [...nextHeaders], rows: nextRows.map((r) => [...r]) },
      ]);
      setHistoryIdx(historyIdx + 1);
    },
    [historyIdx]
  );

  // Update a single cell — state updates stay pure so StrictMode cannot double-record history
  const updateCell = useCallback(
    (rowIndex: number, colIndex: number, value: string) => {
      const updated = editableRows.map((row, rIdx) =>
        rIdx === rowIndex ? row.map((cell, cIdx) => (cIdx === colIndex ? value : cell)) : row
      );
      setEditableRows(updated);
      pushHistory(editableHeaders, updated);
    },
    [editableHeaders, editableRows, pushHistory]
  );

  // Update a header cell
  const updateHeader = useCallback(
    (colIndex: number, value: string) => {
      const updated = [...editableHeaders];
      updated[colIndex] = value;
      setEditableHeaders(updated);
      pushHistory(updated, editableRows);
    },
    [editableHeaders, editableRows, pushHistory]
  );

  const canUndo = historyIdx > 0;
  const canRedo = historyIdx >= 0 && historyIdx < history.length - 1;

  const undo = useCallback(() => {
    if (historyIdx <= 0) return;
    const target = history[historyIdx - 1];
    setEditableHeaders([...target.headers]);
    setEditableRows(target.rows.map((r) => [...r]));
    setHistoryIdx((prev) => prev - 1);
  }, [history, historyIdx]);

  const redo = useCallback(() => {
    if (historyIdx >= history.length - 1) return;
    const target = history[historyIdx + 1];
    setEditableHeaders([...target.headers]);
    setEditableRows(target.rows.map((r) => [...r]));
    setHistoryIdx((prev) => prev + 1);
  }, [history, historyIdx]);

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
            headers: apiHeaders(true),
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

        setSuccessMessage(
          approved
            ? 'Đã lưu và phê duyệt bảng thành công'
            : 'Đã lưu thay đổi bảng, chưa phê duyệt'
        );
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
    updateHeader,
    undo,
    redo,
    canUndo,
    canRedo,
    saveRectification,
    revertToRawBackup,
    revertToCurrentSaved,
    refreshTables: fetchTables,
  };
}
