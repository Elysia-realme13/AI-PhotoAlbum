import request from '@/utils/request'
import type { PhotoItem, PhotoListResponse, PhotoDetail } from '@/types/photo'

export interface PhotoListParams {
  page?: number
  page_size?: number
  sort_by?: string
  order?: string
}

export const photoApi = {
  /** 上传照片 */
  upload(file: File, onProgress?: (pct: number) => void) {
    const formData = new FormData()
    formData.append('files', file)
    return request.post('/photos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total))
      },
    })
  },

  /** 照片列表 */
  list(params: PhotoListParams = {}) {
    return request.get('/photos', { params })
  },

  /** 照片详情 */
  getById(id: string) {
    return request.get(`/photos/${id}`)
  },

  /** 软删除（移入回收站） */
  delete(id: string) {
    return request.delete(`/photos/${id}`)
  },

  /** 恢复 */
  restore(id: string) {
    return request.post(`/photos/${id}/restore`)
  },

  /** 永久删除 */
  permanentDelete(id: string) {
    return request.delete(`/photos/${id}?permanent=true`)
  },

  /** 获取 EXIF 元数据 */
  getMetadata(id: string) {
    return request.get(`/photos/${id}/metadata`)
  },

  /** 缩略图 URL */
  thumbnailUrl(id: string) {
    return `/api/photos/${id}/thumbnail`
  },

  /** 原始文件 URL */
  fileUrl(id: string) {
    return `/api/photos/${id}/file`
  },

  /** 剩余天数 */
  daysLeft(deletedAt: string): number {
    const deleted = new Date(deletedAt)
    const expire = new Date(deleted.getTime() + 7 * 24 * 3600 * 1000)
    const now = new Date()
    return Math.max(0, Math.ceil((expire.getTime() - now.getTime()) / (24 * 3600 * 1000)))
  },
}
