/** 目标检测结果 */
export interface Detection {
  label: string
  confidence: number
  bbox: [number, number, number, number]
}

/** 人脸检测信息 */
export interface FaceInfo {
  face_id: string
  identity_id?: string
  name?: string
  bbox: [number, number, number, number]
  confidence: number
}

/** 后台任务状态 */
export interface TaskInfo {
  task_id: string
  type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: Record<string, unknown>
}

/** AI 描述信息（对应后端 ImageDescription 表） */
export interface ImageDescription {
  description?: string | null
  narrative?: string | null
  tags?: string[] | null
  quality_score?: number | null
  memory_score?: number | null
}

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
  metadata?: Record<string, string | number | boolean | null>
  description?: ImageDescription | null
  detections?: Detection[]
  faces?: FaceInfo[]
  tasks?: TaskInfo[]
}

export interface PhotoListResponse {
  total: number
  page: number
  page_size: number
  items: PhotoItem[]
}

/** 时间轴分组 */
export interface TimelineGroup {
  date: string
  count: number
  cover_photo?: PhotoItem | null
}
