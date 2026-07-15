import request from '@/utils/request'
import type { Album, AlbumPhotosResponse, AlbumCreateParams } from '@/types/album'

/**
 * 相册 API 预留封装。
 *
 * 注意：后端相册接口（Phase 4）尚未实现，当前相册页使用前端按时间分组的
 * 虚拟相册方案。待后端 /api/albums 就绪后，相册页可切换为调用以下接口，
 * 无需改动其余业务代码。
 */
export interface AlbumPhotosParams {
  page?: number
  page_size?: number
}

export const albumApi = {
  /** 相册列表 —— 预留 GET /albums */
  list() {
    return request.get<Album[]>('/albums')
  },

  /** 相册内照片 —— 预留 GET /albums/{id}/photos */
  getPhotos(id: string, params: AlbumPhotosParams = {}) {
    return request.get<AlbumPhotosResponse>(`/albums/${id}/photos`, { params })
  },

  /** 创建相册 —— 预留 POST /albums */
  create(data: AlbumCreateParams) {
    return request.post<Album>('/albums', data)
  },
}
