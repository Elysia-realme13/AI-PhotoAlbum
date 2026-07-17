import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { photoApi } from '@/api/photo'
import { clearPhotosCache } from '@/api/search'
import type { PhotoItem, PhotoDetail } from '@/types/photo'

// 与设置页偏好保持一致的 localStorage key
const PREF_KEY = 'settings.preferences'

export const usePhotoStore = defineStore('photo', () => {
  const photos = ref<PhotoItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(40)
  const order = ref<'asc' | 'desc'>('desc')

  /** 从设置页偏好（localStorage）同步每页数量与排序方向 */
  function loadPrefs() {
    try {
      const raw = localStorage.getItem(PREF_KEY)
      if (!raw) return
      const saved = JSON.parse(raw)
      if (saved.pageSize) pageSize.value = saved.pageSize
      if (saved.sortOrder === 'asc' || saved.sortOrder === 'desc') order.value = saved.sortOrder
    } catch {
      // ignore
    }
  }

  async function fetchPhotos(page = 1) {
    loadPrefs()
    loading.value = true
    try {
      const res = await photoApi.list({ page, page_size: pageSize.value, sort_by: 'photo_time', order: order.value })
      photos.value = res.data.items
      total.value = res.data.total
      currentPage.value = page
    } catch {
      // handled by interceptor
    } finally {
      loading.value = false
    }
  }

  async function uploadPhoto(file: File): Promise<PhotoDetail | null> {
    try {
      const res = await photoApi.upload(file)
      clearPhotosCache()
      await fetchPhotos(currentPage.value)
      return res.data
    } catch (e) {
      console.error('[photo store] 上传失败:', file.name, e)
      return null
    }
  }

  async function removePhoto(id: string) {
    try {
      await photoApi.delete(id)
      ElMessage.success('已移入回收站')
      clearPhotosCache()
      await fetchPhotos(currentPage.value)
    } catch {
      // handled by interceptor
    }
  }

  return {
    photos,
    total,
    loading,
    currentPage,
    pageSize,
    fetchPhotos,
    uploadPhoto,
    removePhoto,
  }
})
