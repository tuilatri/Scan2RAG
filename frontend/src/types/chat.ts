export interface CitationItem {
  id?: string
  document_id?: string
  document_name?: string
  breadcrumb?: string
  page_number: number
  is_table?: boolean
  is_superseded?: boolean
  rerank_score?: number
  snippet?: string
}

// Alias for CitationItem
export type Citation = CitationItem;

export interface StreamEvent {
  event: 'status' | 'citations' | 'token' | 'done' | 'error'
  status?: string
  message?: string
  citations?: CitationItem[]
  token?: string
  provider?: string
  model?: string
  latency_retrieval_ms?: number
  latency_rerank_ms?: number
  latency_total_ms?: number
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  citations?: CitationItem[]
  provider?: string
  model?: string
  complexity?: "simple" | "complex"
  latency_total_ms?: number
  timestamp?: string
}

export interface QueryRequest {
  query: string
  top_k_retrieval?: number
  top_k_rerank?: number
  filter_superseded?: boolean
}

export interface QueryResponse {
  query: string
  answer: string
  citations: CitationItem[]
  provider: string
  model: string
  complexity: string
  latency_retrieval_ms: number
  latency_rerank_ms: number
  latency_total_ms: number
}

export interface CompareRequestData {
  query: string
  thread_id?: string
}

export interface CompareEvidenceItem {
  document_id: string
  chunk_count: number
  citation_ids: (string | null)[]
}

export interface CompareVerification {
  passed: boolean
  unsupported_numbers: Record<string, number>
  checked_numbers: number
}

export interface CompareVersionNote {
  document_id: string
  effective_date?: string | null
  superseded_by?: string | null
  note?: string
}

export interface CompareResponseData {
  query: string
  answer: string
  citations: CitationItem[]
  evidence: CompareEvidenceItem[]
  verification: CompareVerification
  version_notes: CompareVersionNote[]
  plan_source: string
  sub_queries: string[]
  thread_id?: string | null
  history_len: number
  provider: string
  model: string
}
