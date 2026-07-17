import request from '@/utils/request'
import type { PhotoItem, PhotoListResponse, PhotoDetail, TimelineGroup } from '@/types/photo'

export interface PhotoListParams {
  page?: number
  page_size?: number
  sort_by?: string
  order?: string
  is_deleted?: boolean
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

  /** 恢复（从回收站） */
  restore(id: string) {
    return request.post(`/photos/${id}/restore`)
  },

  /** 永久删除 */
  permanentDelete(id: string) {
    return request.delete(`/photos/recycle-bin/${id}/permanent`)
  },

  /** 批量软删除（移入回收站） */
  batchDelete(ids: string[]) {
    return request.post('/photos/batch/delete', { photo_ids: ids })
  },

  /** 批量恢复（从回收站） */
  batchRestore(ids: string[]) {
    return request.post('/photos/recycle-bin/batch/restore', { photo_ids: ids })
  },

  /** 批量永久删除 */
  batchPermanentDelete(ids: string[]) {
    return request.post('/photos/recycle-bin/batch/permanent', { photo_ids: ids })
  },

  /** 获取 EXIF 元数据 */
  getMetadata(id: string) {
    return request.get(`/photos/${id}/metadata`)
  },

  /** 手动触发重新 AI 分析（创建指定类型的任务） */
  reanalyze(id: string, tasks: string[]) {
    return request.post<{ photo_id: string; tasks: { task_id: string; task_type: string }[] }>(
      `/photos/${id}/reanalyze`,
      { tasks }
    )
  },

  /** 照片时间轴（按年/月/日分组） */
  timeline(group_by: 'year' | 'month' | 'day' = 'month') {
    return request.get<TimelineGroup[]>('/photos/timeline/list', { params: { group_by } })
  },

  /** 一键优化存储（重新压缩原图 + 重建缩略图） */
  optimizeStorage() {
    return request.post<{
      processed: number
      skipped: number
      before_bytes: number
      after_bytes: number
      freed_bytes: number
    }>('/photos/optimize-storage')
  },

  /** 缩略图 URL（带 Token 认证） */
  thumbnailUrl(id: string) {
    const token = localStorage.getItem('token')
    const qs = token ? `?token=${token}` : ''
    return `/api/photos/${id}/thumbnail${qs}`
  },

  /** 原始文件 URL（带 Token 认证） */
  fileUrl(id: string) {
    const token = localStorage.getItem('token')
    const qs = token ? `?token=${token}` : ''
    return `/api/photos/${id}/file${qs}`
  },

  /** 剩余天数 */
  daysLeft(deletedAt: string): number {
    const deleted = new Date(deletedAt)
    const expire = new Date(deleted.getTime() + 7 * 24 * 3600 * 1000)
    const now = new Date()
    return Math.max(0, Math.ceil((expire.getTime() - now.getTime()) / (24 * 3600 * 1000)))
  },
}
