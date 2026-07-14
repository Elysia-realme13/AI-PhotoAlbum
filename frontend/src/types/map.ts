/** 照片 GPS 位置信息 */
export interface PhotoLocation {
  id: string
  latitude: number
  longitude: number
  city?: string
  province?: string
  country?: string
  photo_time?: string
  original_name?: string
}
