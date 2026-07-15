/** 搜索筛选条件 */
export interface SearchFilters {
  start_date?: string // YYYY-MM-DD
  end_date?: string // YYYY-MM-DD
  city?: string
  tags?: string[]
}

/** 搜索模式 */
export type SearchMode = 'semantic' | 'keyword' | 'tag'

/** 搜索请求 */
export interface SearchRequest {
  query: string
  mode?: SearchMode
  filters?: SearchFilters
  page?: number
  page_size?: number
}

/** 搜索结果项 */
export interface SearchResultItem {
  id: string
  thumbnail_url: string
  original_name?: string
  photo_time?: string
  city?: string
  /** 语义搜索相似度 0~1 */
  score?: number
  tags: string[]
}

/** 搜索响应 */
export interface SearchResponse {
  items: SearchResultItem[]
  total: number
  query: string
  mode: SearchMode
  suggested_tags: string[]
}
