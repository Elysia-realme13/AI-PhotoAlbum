<template>
  <div
    class="group relative aspect-square rounded-lg overflow-hidden bg-gray-100 cursor-pointer shadow-sm hover:shadow-md transition-shadow"
    @click="$emit('click')"
  >
    <!-- 缩略图 -->
    <img
      :src="thumbnailUrl"
      :alt="photo.original_name || '照片'"
      class="w-full h-full object-cover"
      loading="lazy"
    />

    <!-- 悬停遮罩 -->
    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-end">
      <div class="p-2 w-full opacity-0 group-hover:opacity-100 transition-opacity">
        <p v-if="photo.photo_time" class="text-white text-xs truncate">
          {{ formatDate(photo.photo_time) }}
        </p>
      </div>
    </div>

    <!-- 操作按钮 -->
    <button
      class="absolute top-1 right-9 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500"
      @click.stop="$emit('detail')"
      title="详情"
    >
      <el-icon :size="14"><InfoFilled /></el-icon>
    </button>
    <button
      class="absolute top-1 right-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
      @click.stop="$emit('delete')"
      title="删除"
    >
      <el-icon :size="14"><Delete /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { Delete, InfoFilled } from '@element-plus/icons-vue'
import type { PhotoItem } from '@/types/photo'
import { photoApi } from '@/api/photo'

const props = defineProps<{
  photo: PhotoItem
}>()

defineEmits<{
  click: []
  detail: []
  delete: []
}>()

const thumbnailUrl = photoApi.thumbnailUrl(props.photo.id)

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>
