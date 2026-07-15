export interface PhotoItem {
  id: string
  filename: string
  original_name?: string
  file_path: string
  file_size?: number
  width?: number
  height?: number
  photo_time?: string
  upload_time?: string
  file_type: string
  md5?: string
  is_deleted: boolean
  deleted_at?: string
  processed_tasks?: Record<string, boolean>
}
