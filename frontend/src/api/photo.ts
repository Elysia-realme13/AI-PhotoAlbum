import request from '@/utils/request'
import type { PhotoItem, PhotoListResponse, PhotoDetail } from '@/types/photo'

export interface PhotoListParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export const photoApi = {
  /** 上传照片 */
  upload(file: File, onProgress?: (pct: number) => void) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<PhotoDetail>('/photos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total))
      },
    })
  },

  /** 照片列表 */
  list(params: PhotoListParams = {}) {
    return request.get<PhotoListResponse>('/photos', { params })
  },

  /** 照片详情 */
  getById(id: string) {
    return request.get<PhotoDetail>(`/photos/${id}`)
  },

  /** 软删除 */
  delete(id: string) {
    return request.delete(`/photos/${id}`)
  },

  /** 恢复 */
  restore(id: string) {
    return request.post(`/photos/${id}/restore`)
  },

  /** 获取 EXIF 元数据 */
  getMetadata(id: string) {
    return request.get(`/photos/${id}/metadata`)
  },

  /** 缩略图 URL */
  thumbnailUrl(id: string) {
    return `/api/medias/${id}/thumbnail`
  },

  /** 原始文件 URL */
  fileUrl(id: string) {
    return `/api/medias/${id}/file`
  },
}
