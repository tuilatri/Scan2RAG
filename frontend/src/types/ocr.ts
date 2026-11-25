export interface TableSummary {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  title: string;
  rows_count: number;
  cols_count: number;
  vlm_rectified: boolean;
  hitl_approved: boolean;
  hitl_rectified: boolean;
}

export interface TableDetail {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  title: string;
  content: string;
  raw_content_backup?: string | null;
  headers: string[];
  rows: string[][];
  metadata?: Record<string, unknown>;
}

export interface RectifyRequest {
  content: string;
  approved?: boolean;
  reviewer_notes?: string;
}

export interface TableCellCoord {
  rowIndex: number;
  colIndex: number;
}
