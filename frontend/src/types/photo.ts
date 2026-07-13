export interface PhotoItem {
  id: string
  owner_id?: string
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
  processed_tasks?: Record<string, boolean>
}

export interface PhotoMetadata {
  id?: string
  photo_id?: string
  camera_make?: string
  camera_model?: string
  lens_model?: string
  focal_length?: number
  aperture?: number
  shutter_speed?: string
  iso?: number
  latitude?: number
  longitude?: number
  altitude?: number
  country?: string
  province?: string
  city?: string
  district?: string
  address?: string
}

export interface PhotoDetail extends PhotoItem {
  metadata?: PhotoMetadata
}

export interface PhotoListResponse {
  total: number
  page: number
  page_size: number
  items: PhotoItem[]
}
