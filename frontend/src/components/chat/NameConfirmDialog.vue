<template>
  <div class="my-3 rounded-xl border border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-900/20 overflow-hidden">
    <!-- 头部提示 -->
    <div class="px-4 py-3 border-b border-blue-100 dark:border-blue-800">
      <p class="text-sm text-gray-700 dark:text-dark-text">
        <el-icon class="inline align-middle mr-1 text-blue-500"><QuestionFilled /></el-icon>
        我找到了几个未命名的人脸聚类，请确认「<strong>{{ personName }}</strong>」对应的是哪一位？
      </p>
    </div>

    <!-- 候选聚类网格 -->
    <div class="p-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
      <button
        v-for="candidate in candidates"
        :key="candidate.cluster_id"
        :class="[
          'group relative rounded-lg border-2 overflow-hidden transition-all aspect-square',
          selectedId === candidate.cluster_id
            ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800'
            : 'border-gray-200 dark:border-dark-border hover:border-blue-300'
        ]"
        @click="selectedId = candidate.cluster_id"
      >
        <!-- 缩略图 -->
        <div class="w-full h-full bg-gray-100 dark:bg-dark-hover flex items-center justify-center">
          <img
            v-if="getThumbnailUrl(candidate)"
            :src="getThumbnailUrl(candidate)"
            class="w-full h-full object-cover"
            alt="人脸聚类"
          />
          <div v-else class="flex flex-col items-center text-gray-400">
            <el-icon :size="32"><UserFilled /></el-icon>
            <span class="text-xs mt-1">{{ candidate.face_count }} 张人脸</span>
          </div>
        </div>

        <!-- 选中角标 -->
        <div
          v-if="selectedId === candidate.cluster_id"
          class="absolute top-1 right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center"
        >
          <el-icon :size="12" color="white"><Check /></el-icon>
        </div>

        <!-- 底部信息 -->
        <div class="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs px-2 py-1">
          {{ candidate.face_count }} 张人脸
        </div>
      </button>
    </div>

    <!-- 操作按钮 -->
    <div class="px-4 pb-4 flex gap-2 justify-end">
      <el-button size="small" @click="$emit('skip')">跳过</el-button>
      <el-button
        size="small"
        type="primary"
        :disabled="!selectedId"
        :loading="confirming"
        @click="handleConfirm"
      >
        确认
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { QuestionFilled, UserFilled, Check } from '@element-plus/icons-vue'
import { agentApi } from '@/api/agent'

export interface CandidateCluster {
  cluster_id: string
  face_count: number
  representative_faces?: Array<{
    face_id: number
    photo_id: string
    thumbnail_url?: string
    rect?: number[]
    confidence?: number
  }>
  identity_name?: string | null
}

const props = defineProps<{
  candidates: CandidateCluster[]
  personName: string
  sessionId: string
  query: string
}>()

const emit = defineEmits<{
  (e: 'confirmed', data: { cluster_id: string; name: string }): void
  (e: 'skip'): void
}>()

const selectedId = ref<string>('')
const confirming = ref(false)

function getThumbnailUrl(candidate: CandidateCluster): string {
  const faces = candidate.representative_faces
  if (!faces || faces.length === 0) return ''
  const face = faces[0]
  // 优先使用 thumbnail_url，否则构造 medias 路径
  if (face.thumbnail_url) return face.thumbnail_url
  if (face.photo_id) return `/api/medias/${face.photo_id}/thumbnail`
  return ''
}

async function handleConfirm() {
  if (!selectedId.value) return
  confirming.value = true
  try {
    await agentApi.confirmName({
      cluster_id: selectedId.value,
      name: props.personName,
      session_id: props.sessionId,
      query: props.query,
    })
    emit('confirmed', { cluster_id: selectedId.value, name: props.personName })
  } catch {
    // handled by interceptor
  } finally {
    confirming.value = false
  }
}
</script>
