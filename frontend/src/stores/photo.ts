import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { photoApi } from '@/api/photo'
import { clearPhotosCache } from '@/api/search'
import type { PhotoItem, PhotoDetail } from '@/types/photo'

export const usePhotoStore = defineStore('photo', () => {
  const photos = ref<PhotoItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)

  async function fetchPhotos(page = 1) {
    loading.value = true
    try {
      const res = await photoApi.list({ page, page_size: pageSize.value, sort_by: 'photo_time' })
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
