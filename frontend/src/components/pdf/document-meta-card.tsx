import React, { useEffect, useState } from 'react';
import { AlertTriangle, Calendar, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { API_BASE_URL, apiHeaders } from '@/lib/api-config';

interface DocumentMetaCardProps {
  docId: string;
}

interface DocumentMeta {
  title: string;
  effective_date: string;
  is_superseded: boolean;
  superseded_by?: string | null;
  description: string;
  pages_count?: number;
}

const formatDate = (value?: string) => {
  if (!value) return 'Chưa cập nhật';
  const [year, month, day] = value.split('-');
  return year && month && day ? `${day}/${month}/${year}` : value;
};

export const DocumentMetaCard: React.FC<DocumentMetaCardProps> = ({ docId }) => {
  const [meta, setMeta] = useState<DocumentMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);

    fetch(`${API_BASE_URL}/api/v1/documents/${encodeURIComponent(docId)}`, {
      headers: apiHeaders(),
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Lỗi tải thông tin văn bản: ${res.status}`);
        return res.json() as Promise<DocumentMeta>;
      })
      .then((data) => {
        if (!controller.signal.aborted) setMeta(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) setMeta(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [docId]);

  const isSuperseded = meta?.is_superseded === true;

  return (
    <div className="border-b bg-muted/30 px-3 py-2 pr-4 text-xs" aria-busy={isLoading}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          <FileText className="h-3.5 w-3.5 text-primary shrink-0" aria-hidden="true" />
          <span className="font-semibold text-foreground truncate">{meta?.title || docId}</span>
        </div>
        <div className="shrink-0 flex items-center space-x-1">
          {isLoading ? (
            <span className="text-[10px] text-muted-foreground">Đang tải thông tin...</span>
          ) : !meta ? (
            <Badge variant="outline" className="h-4 px-1.5 text-[9px]">
              Chưa có thông tin
            </Badge>
          ) : isSuperseded ? (
            <Badge variant="destructive" className="h-4 px-1.5 text-[9px]">
              Đã sửa đổi
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="h-4 px-1.5 text-[9px] border-emerald-500/40 text-emerald-600 dark:text-emerald-400"
            >
              Hiệu lực
            </Badge>
          )}
        </div>
      </div>

      {meta?.effective_date && (
        <p className="mt-1 flex items-center text-[10px] text-muted-foreground">
          <Calendar className="h-2.5 w-2.5 mr-1 shrink-0" aria-hidden="true" />
          Hiệu lực từ {formatDate(meta.effective_date)}
        </p>
      )}

      {isSuperseded && meta.superseded_by && (
        <div
          role="status"
          className="mt-1 flex items-center space-x-1 text-[10px] text-amber-700 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20"
        >
          <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
          <span>Lưu ý: Một số điều đã được sửa đổi bởi {meta.superseded_by}.</span>
        </div>
      )}

      {meta?.description && (
        <p className="mt-1 text-[11px] text-muted-foreground line-clamp-1 leading-snug">
          {meta.description}
        </p>
      )}
    </div>
  );
};
