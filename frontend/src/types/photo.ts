export interface PhotoItem {
  id: string
  filename: string
  original_name?: string
  file_path?: string
  file_size?: number
  width?: number
  height?: number
  photo_time?: string
  upload_time?: string
  file_type?: string
  md5?: string
  is_deleted?: boolean
  deleted_at?: string
  tags?: string[] | null
  quality_score?: number | null
  processed_tasks?: Record<string, boolean>
  thumbnail_url?: string
}

export interface PhotoDetail extends PhotoItem {
  metadata?: Record<string, any>
  detections?: any[]
  faces?: any[]
  tasks?: any[]
}

export interface PhotoListResponse {
  total: number
  page: number
  page_size: number
  items: PhotoItem[]
}
