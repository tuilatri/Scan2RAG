import React from 'react';
import { ShieldCheck, AlertTriangle, FileText, Calendar } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface DocumentMetaCardProps {
  docId: string;
}

const DOCUMENT_INFO_MAP: Record<
  string,
  {
    title: string;
    effectiveDate: string;
    isSuperseded: boolean;
    supersededBy?: string;
    description: string;
  }
> = {
  thông_tư_88: {
    title: 'Thông tư số 88/VBHN-BQP',
    effectiveDate: '31/12/2023',
    isSuperseded: false,
    description:
      'Văn bản hợp nhất quy định tiêu chuẩn sức khỏe, khám sức khỏe thực hiện nghĩa vụ quân sự (Hiệu lực cao nhất hiện hành).',
  },
  thông_tư_105: {
    title: 'Thông tư số 105/2023/TT-BQP',
    effectiveDate: '06/12/2023',
    isSuperseded: true,
    supersededBy: 'Thông tư 106 & VBHN 88',
    description:
      'Quy định tiêu chuẩn sức khỏe, khám sức khỏe thực hiện nghĩa vụ quân sự (Một số điều đã được sửa đổi).',
  },
  thông_tư_106: {
    title: 'Thông tư số 106/2024/TT-BQP',
    effectiveDate: '15/05/2024',
    isSuperseded: false,
    description:
      'Sửa đổi, bổ sung một số điều của Thông tư số 105/2023/TT-BQP về tiêu chuẩn sức khỏe nghĩa vụ quân sự.',
  },
  thông_tư_68: {
    title: 'Thông tư số 68/2020/TT-BQP',
    effectiveDate: '20/05/2020',
    isSuperseded: false,
    description: 'Quy định chi tiết việc thi hành một số điều của Luật Nghĩa vụ quân sự.',
  },
  hướng_dẫn_cục_quân_y: {
    title: 'Hướng dẫn số 259/HD-QY Cục Quân Y',
    effectiveDate: '10/01/2024',
    isSuperseded: false,
    description:
      'Hướng dẫn chuyên môn về phân loại thể lực và khám bệnh chuyên khoa phục vụ tuyển quân.',
  },
};

export const DocumentMetaCard: React.FC<DocumentMetaCardProps> = ({ docId }) => {
  const meta = DOCUMENT_INFO_MAP[docId] || {
    title: docId,
    effectiveDate: 'Chưa cập nhật',
    isSuperseded: false,
    description: 'Tài liệu quy phạm pháp luật trong cơ sở dữ liệu Scan2RAG.',
  };

  return (
    <div className="border-b bg-muted/30 px-3 py-2 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-1.5 overflow-hidden">
          <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
          <span className="font-semibold text-foreground truncate">{meta.title}</span>
        </div>
        <div className="shrink-0 flex items-center space-x-1">
          {meta.isSuperseded ? (
            <Badge variant="destructive" className="h-4 px-1.5 text-[9px]">
              Đã sửa đổi
            </Badge>
          ) : (
            <Badge variant="outline" className="h-4 px-1.5 text-[9px] border-emerald-500/40 text-emerald-600 dark:text-emerald-400">
              Hiệu lực
            </Badge>
          )}
        </div>
      </div>

      {meta.isSuperseded && meta.supersededBy && (
        <div className="mt-1 flex items-center space-x-1 text-[10px] text-amber-700 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <span>Lưu ý: Một số điều đã được sửa đổi bởi {meta.supersededBy}.</span>
        </div>
      )}

      <p className="mt-1 text-[11px] text-muted-foreground line-clamp-1 leading-snug">
        {meta.description}
      </p>
    </div>
  );
};
