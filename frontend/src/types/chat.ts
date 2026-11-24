export interface CitationItem {
  id?: string
  document_id?: string
  document_name?: string
  breadcrumb?: string
  page_number: number
  is_table: boolean
  rerank_score: number
  snippet: string
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
