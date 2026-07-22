<template>
  <div>
    <div class="mb-4">
      <el-segmented v-model="groupBy" :options="groupOptions" size="small" @change="fetchTimeline" />
    </div>

    <div v-loading="loading" class="min-h-[200px]">
      <el-empty v-if="!loading && groups.length === 0" description="暂无照片" />

      <el-timeline v-else>
        <el-timeline-item
          v-for="group in groups"
          :key="group.date"
          :timestamp="group.date"
          placement="top"
        >
          <div class="flex items-center gap-3">
            <div
              v-if="group.cover_photo"
              class="w-20 h-20 rounded-lg overflow-hidden bg-gray-100 dark:bg-dark-hover cursor-pointer shrink-0"
              @click="group.cover_photo && emit('detail', group.cover_photo.id)"
            >
              <img
                :src="photoApi.thumbnailUrl(group.cover_photo.id)"
                class="w-full h-full object-cover"
                :alt="group.date"
              />
            </div>
            <div>
              <p class="text-sm font-medium text-gray-800 dark:text-dark-text">{{ group.date }}</p>
              <p class="text-xs text-gray-400 dark:text-dark-text-secondary">{{ group.count }} 张照片</p>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { photoApi } from '@/api/photo'
import type { TimelineGroup } from '@/types/photo'

const emit = defineEmits<{
  detail: [id: string]
}>()

type GroupBy = 'year' | 'month' | 'day'

const groupBy = ref<GroupBy>('month')
const groupOptions = [
  { label: '按年', value: 'year' },
  { label: '按月', value: 'month' },
  { label: '按日', value: 'day' },
]

const loading = ref(false)
const groups = ref<TimelineGroup[]>([])

async function fetchTimeline() {
  loading.value = true
  try {
    const res = await photoApi.timeline(groupBy.value)
    groups.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTimeline()
})
</script>
