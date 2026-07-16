<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">回收站</h2>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      <div v-for="i in 6" :key="i" class="aspect-square rounded-lg bg-gray-200 dark:bg-dark-hover animate-pulse" />
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="photos.length === 0" description="回收站是空的" />

    <!-- 已删除照片列表 -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      <div
        v-for="photo in photos"
        :key="photo.id"
        class="bg-white dark:bg-dark-card rounded-lg border border-gray-200 dark:border-dark-border overflow-hidden shadow-sm"
      >
        <!-- 缩略图 -->
        <div class="aspect-square relative bg-gray-100 dark:bg-dark-hover">
          <img
            :src="photoApi.thumbnailUrl(photo.id)"
            class="w-full h-full object-cover opacity-60"
          />
          <!-- 剩余天数角标 -->
          <span
            :class="[
              'absolute top-2 left-2 text-xs px-2 py-0.5 rounded-full font-medium',
              daysLeft(photo) <= 1
                ? 'bg-red-500 text-white'
                : 'bg-yellow-500 text-white'
            ]"
          >
            {{ daysLeft(photo) <= 1 ? '即将过期' : `剩余 ${daysLeft(photo)} 天` }}
          </span>
        </div>

        <!-- 操作按钮 -->
        <div class="p-2 flex gap-2">
          <el-button
            size="small"
            type="primary"
            :icon="RefreshRight"
            @click="handleRestore(photo)"
          >
            恢复
          </el-button>
          <el-button
            size="small"
            type="danger"
            :icon="Delete"
            @click="handlePermanentDelete(photo)"
          >
            彻底删除
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, RefreshRight } from '@element-plus/icons-vue'
import { photoApi } from '@/api/photo'
import type { PhotoItem } from '@/types/photo'

const photos = ref<PhotoItem[]>([])
const loading = ref(false)

function daysLeft(photo: PhotoItem): number {
  if (!photo.deleted_at) return 0
  return photoApi.daysLeft(photo.deleted_at)
}

async function fetchRecycleBin() {
  loading.value = true
  try {
    const res = await photoApi.list({ is_deleted: true })
    photos.value = res.data.items || []
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handleRestore(photo: PhotoItem) {
  try {
    await photoApi.restore(photo.id)
    ElMessage.success('照片已恢复')
    await fetchRecycleBin()
  } catch {
    // handled by interceptor
  }
}

async function handlePermanentDelete(photo: PhotoItem) {
  try {
    await ElMessageBox.confirm(
      '彻底删除后无法恢复，确定要删除吗？',
      '确认彻底删除',
      { confirmButtonText: '彻底删除', cancelButtonText: '取消', type: 'warning' }
    )
    await photoApi.permanentDelete(photo.id)
    ElMessage.success('已彻底删除')
    await fetchRecycleBin()
  } catch {
    // cancelled
  }
}

onMounted(fetchRecycleBin)
</script>
