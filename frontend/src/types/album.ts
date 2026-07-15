import type { PhotoItem } from '@/types/photo'

/** 相册（后端 Phase 4 待实现的数据结构预留） */
export interface Album {
  id: string
  name: string
  cover_photo_id?: string
  photo_count: number
  created_at?: string
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
  photo_ids?: string[]
}
