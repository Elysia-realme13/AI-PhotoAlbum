<template>
  <div
    class="group relative aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-dark-hover cursor-pointer shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
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

    <!-- 检测标签 -->
    <div v-if="tagSummary.length" class="absolute bottom-0 left-0 right-0 px-2 pb-1 flex flex-wrap gap-1">
      <span
        v-for="tag in tagSummary.slice(0, 4)"
        :key="tag.label"
        class="px-1.5 py-0.5 rounded text-[10px] font-medium leading-tight"
        :style="'background: ' + (tag.max_confidence >= 0.8 ? '#166534cc' : '#854d0ecc') + '; color: white;'"
      >
        {{ tag.label }}
        <small>x{{ tag.count }}</small>
      </span>
    </div>    <!-- 选择模式：左上角 checkbox -->
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
      <!-- 回收站模式：恢复 + 彻底删除 -->
      <template v-if="recycleMode">
        <button
          class="absolute top-1 right-9 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-green-500"
          @click.stop="$emit('restore')"
          title="恢复"
        >
          <el-icon :size="14"><RefreshRight /></el-icon>
        </button>
        <button
          class="absolute top-1 right-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
          @click.stop="$emit('delete')"
          title="彻底删除"
        >
          <el-icon :size="14"><Delete /></el-icon>
        </button>
      </template>
      <!-- 普通模式：详情 + 删除 -->
      <template v-else>
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Delete, InfoFilled, Check, RefreshRight } from '@element-plus/icons-vue'
import type { PhotoItem, TagSummaryItem } from '@/types/photo'
import { photoApi } from '@/api/photo'

const props = defineProps<{
  photo: PhotoItem
  selectable?: boolean
  selected?: boolean
  recycleMode?: boolean
}>()

// 标签兼容字典结构：仅当 tags 为对象且含 summary 时提取，否则空数组
const tagSummary = computed<TagSummaryItem[]>(() => {
  const t = props.photo.tags
  if (t && !Array.isArray(t) && Array.isArray(t.summary)) return t.summary
  return []
})

defineEmits<{
  click: []
  detail: []
  delete: []
  restore: []
  select: [id: string]
}>()

const thumbnailUrl = photoApi.thumbnailUrl(props.photo.id)

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>
