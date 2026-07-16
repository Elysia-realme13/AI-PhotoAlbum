<template>
  <div
    class="group relative aspect-square rounded-lg overflow-hidden bg-gray-100 cursor-pointer shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
    :class="{ 'ring-2 ring-blue-500': selected }"
    @click="$emit('click')"
  >
    <!-- 缩略图 -->
    <img
      :src="thumbnailUrl"
      :alt="photo.original_name || '照片'"
      class="w-full h-full object-cover"
      loading="lazy"
    />

    <!-- 选择模式：左上角 checkbox -->
    <div
      v-if="selectable"
      class="absolute top-2 left-2 z-10"
      @click.stop="$emit('select', photo.id)"
    >
      <div
        class="w-6 h-6 rounded border-2 flex items-center justify-center transition-colors"
        :class="selected ? 'bg-blue-500 border-blue-500' : 'bg-white/80 border-gray-300 hover:border-blue-400'"
      >
        <el-icon v-if="selected" :size="14" color="#fff"><Check /></el-icon>
      </div>
    </div>

    <!-- 悬停遮罩 -->
    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-end">
      <div class="p-2 w-full opacity-0 group-hover:opacity-100 transition-opacity">
        <p v-if="photo.photo_time" class="text-white text-xs truncate">
          {{ formatDate(photo.photo_time) }}
        </p>
      </div>
    </div>

    <!-- 操作按钮（选择模式下隐藏） -->
    <template v-if="!selectable">
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { Delete, InfoFilled, Check } from '@element-plus/icons-vue'
import type { PhotoItem } from '@/types/photo'
import { photoApi } from '@/api/photo'

const props = defineProps<{
  photo: PhotoItem
  selectable?: boolean
  selected?: boolean
}>()

defineEmits<{
  click: []
  detail: []
  delete: []
  select: [id: string]
}>()

const thumbnailUrl = photoApi.thumbnailUrl(props.photo.id)

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>
