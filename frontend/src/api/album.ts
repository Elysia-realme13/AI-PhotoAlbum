import request from '@/utils/request'
import type { Album, AlbumPhotosResponse, AlbumCreateParams } from '@/types/album'

/**
 * 相册 API
 */
export interface AlbumPhotosParams {
  page?: number
  page_size?: number
}

export const albumApi = {
  /** 相册列表 */
  list() {
    return request.get<Album[]>('/albums')
  },

  /** 相册详情 */
  getById(id: string) {
    return request.get<Album>(`/albums/${id}`)
  },

  /** 创建相册 */
  create(data: AlbumCreateParams) {
    return request.post<Album>('/albums', data)
  },

  /** 更新相册 */
  update(id: string, data: Partial<AlbumCreateParams>) {
    return request.put<Album>(`/albums/${id}`, data)
  },

  /** 删除相册 */
  delete(id: string) {
    return request.delete(`/albums/${id}`)
  },

  /** 相册内照片 */
  getPhotos(id: string, params: AlbumPhotosParams = {}) {
    return request.get<AlbumPhotosResponse>(`/albums/${id}/photos`, { params })
  },

  /** 将照片添加到相册 */
  addPhoto(albumId: string, photoId: string) {
    return request.post(`/albums/${albumId}/photos/${photoId}`)
  },

  /** 从相册移除照片 */
  removePhoto(albumId: string, photoId: string) {
    return request.delete(`/albums/${albumId}/photos/${photoId}`)
  },
}
