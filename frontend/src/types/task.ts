/** 后台任务状态 */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

/** 任务项（对应后端 TaskResponse） */
export interface TaskItem {
  id: string
  photo_id?: string | null
  task_type: string
  status: TaskStatus
  progress?: Record<string, unknown>
  result?: Record<string, unknown>
  error_message?: string | null
  created_at: string
  updated_at?: string | null
}

/** 任务统计（对应后端 TaskStatsResponse） */
export interface TaskStats {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
}

/** 任务类型中文标签（对应后端 TaskType 枚举） */
export const TASK_TYPE_LABELS: Record<string, string> = {
  face_detect: '人脸检测',
  face_cluster: '人脸聚类',
  image_description: '画面描述',
  image_embedding: '向量嵌入',
  quality_assessment: '质量评分',
  thumbnail_generate: '缩略图生成',
  exif_extract: 'EXIF 提取',
  dedup_check: '重复检测',
  object_detection: '目标检测',
}

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

/** 任务状态展示元数据（标签文案 + el-tag 类型） */
export const TASK_STATUS_META: Record<TaskStatus, { label: string; type: TagType }> = {
  pending: { label: '等待中', type: 'info' },
  running: { label: '执行中', type: 'primary' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

/** 重新分析对话框可选的任务类型 */
export const REANALYZE_TASK_OPTIONS: { label: string; value: string }[] = [
  { label: '画面描述', value: 'image_description' },
  { label: '向量嵌入', value: 'image_embedding' },
  { label: '质量评分', value: 'quality_assessment' },
  { label: '人脸检测', value: 'face_detect' },
  { label: '目标检测', value: 'object_detection' },
  { label: 'EXIF 提取', value: 'exif_extract' },
]
