/** 目标检测结果 */
export interface Detection {
  label: string
  confidence: number
  bbox: [number, number, number, number] // x1, y1, x2, y2
}

/** 目标检测标签汇总项（YOLO 聚合后的单个类别） */
export interface DetectionSummaryItem {
  label: string
  count: number
  max_confidence: number
}

/** ImageDescription.tags 的规范结构（后端统一存为对象） */
export interface PhotoTags {
  detections?: Detection[]
  summary?: DetectionSummaryItem[]
  total?: number
  model?: string
}

/** AI 描述（对应后端 PhotoDescriptionResponse） */
export interface PhotoDescription {
  description?: string | null
  narrative?: string | null
  tags?: PhotoTags | null
  quality_score?: number | null
  memory_score?: number | null
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
  tags?: PhotoTags | null
  quality_score?: number | null
  processed_tasks?: Record<string, boolean>
  thumbnail_url?: string
}

export interface PhotoDetail extends PhotoItem {
  metadata?: Record<string, string | number | boolean | null>
  description?: PhotoDescription | null
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
  date: string // "2025-07" 或 "2025-07-14" 取决于 group_by
  count: number
  cover_photo?: PhotoItem | null
}
