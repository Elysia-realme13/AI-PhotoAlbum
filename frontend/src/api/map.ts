import request from '@/utils/request'
import type { PhotoLocation } from '@/types/map'

export const mapApi = {
  /** 获取所有有 GPS 坐标的照片位置 */
  getLocations() {
    return request.get<PhotoLocation[]>('/photos/locations')
  },
}
