import type { PhotoItem } from '@/types/photo'

/** 相册（对齐后端 AlbumResponse） */
export interface Album {
  id: string
  owner_id: string
  name: string
  description?: string | null
  cover_photo_id?: string | null
  is_system: boolean
  album_type: string
  conditions?: Record<string, unknown> | null
  photo_count: number
  created_at: string
  updated_at?: string | null
}

/** 相册内照片列表响应 */
export interface AlbumPhotosResponse {
  total: number
  page: number
  page_size: number
  items: PhotoItem[]
}

/** 创建相册入参 */
export interface AlbumCreateParams {
  name: string
  description?: string
  album_type?: string
  conditions?: Record<string, unknown>
}

/** 更新相册入参 */
export interface AlbumUpdateParams {
  name?: string
  description?: string
  cover_photo_id?: string
}
