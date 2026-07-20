<template>
  <el-drawer
    v-model="drawerVisible"
    title="照片详情"
    direction="rtl"
    size="380px"
  >
    <!-- 加载态 -->
    <div v-if="loading" class="px-1">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="detail" class="detail-body">
      <!-- 顶部大图 -->
      <div class="preview-box" @click="previewVisible = true">
        <img :src="fileUrl" :alt="detail.original_name || '照片'" class="preview-img" />
      </div>

      <!-- 基本信息 -->
      <el-descriptions title="基本信息" :column="1" border size="small" class="mt-4">
        <el-descriptions-item label="文件名">
          {{ detail.original_name || detail.filename }}
        </el-descriptions-item>
        <el-descriptions-item label="尺寸">{{ dimensions }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatFileSize(detail.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ detail.file_type || '—' }}</el-descriptions-item>
        <el-descriptions-item label="拍摄时间">{{ formatDateTime(detail.photo_time) }}</el-descriptions-item>
        <el-descriptions-item label="上传时间">{{ formatDateTime(detail.upload_time) }}</el-descriptions-item>
      </el-descriptions>

      <!-- 相机信息 -->
      <el-descriptions
        v-if="hasCameraInfo"
        title="相机信息"
        :column="1"
        border
        size="small"
        class="mt-4"
      >
        <el-descriptions-item v-if="meta?.camera_make" label="厂商">{{ meta?.camera_make }}</el-descriptions-item>
        <el-descriptions-item v-if="meta?.camera_model" label="型号">{{ meta?.camera_model }}</el-descriptions-item>
        <el-descriptions-item v-if="meta?.lens_model" label="镜头">{{ meta?.lens_model }}</el-descriptions-item>
        <el-descriptions-item v-if="meta?.focal_length" label="焦距">{{ meta?.focal_length }}mm</el-descriptions-item>
        <el-descriptions-item v-if="meta?.aperture" label="光圈">f/{{ meta?.aperture }}</el-descriptions-item>
        <el-descriptions-item v-if="meta?.shutter_speed" label="快门">{{ meta?.shutter_speed }}</el-descriptions-item>
        <el-descriptions-item v-if="meta?.iso" label="ISO">{{ meta?.iso }}</el-descriptions-item>
      </el-descriptions>

      <!-- 位置信息 -->
      <el-descriptions title="位置信息" :column="1" border size="small" class="mt-4">
        <template v-if="hasLocation">
          <el-descriptions-item v-if="locationText" label="地点">{{ locationText }}</el-descriptions-item>
          <el-descriptions-item v-if="meta?.address" label="详细地址">{{ meta?.address }}</el-descriptions-item>
          <el-descriptions-item v-if="hasCoords" label="GPS 坐标">
            {{ Number(meta?.latitude).toFixed(6) }}, {{ Number(meta?.longitude).toFixed(6) }}
          </el-descriptions-item>
        </template>
        <el-descriptions-item v-else label="位置">
          <span class="text-gray-400">无位置信息</span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- AI 分析 -->
      <el-descriptions
        v-if="hasAiInfo"
        title="AI 分析"
        :column="1"
        border
        size="small"
        class="mt-4"
      >
        <el-descriptions-item v-if="aiTags.length > 0" label="标签">
          <div class="flex flex-wrap gap-1">
            <el-tag
              v-for="tag in aiTags"
              :key="tag"
              size="small"
              type="primary"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </el-descriptions-item>
        <el-descriptions-item v-if="aiDesc" label="画面描述">
          <span class="text-sm text-gray-700">{{ aiDesc }}</span>
        </el-descriptions-item>
        <el-descriptions-item v-if="detail?.description?.narrative" label="一句话">
          {{ detail?.description?.narrative }}
        </el-descriptions-item>
        <el-descriptions-item v-if="hasScores" label="评分">
          <span v-if="qualityScore != null" class="mr-3">
            美观度: <b class="text-blue-600">{{ qualityScore }}</b>
          </span>
          <span v-if="memoryScore != null">
            回忆价值: <b class="text-purple-600">{{ memoryScore }}</b>
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 操作区 -->
      <div class="mt-4 flex flex-wrap gap-2">
        <el-button type="primary" plain size="small" @click="openAddToAlbumDialog">
          添加到相册
        </el-button>
        <el-button type="warning" plain size="small" @click="openReanalyzeDialog">
          重新分析
        </el-button>
      </div>
    </div>

    <!-- 无数据 -->
    <el-empty v-else description="暂无详情" />

    <!-- 大图预览 -->
    <el-image-viewer
      v-if="previewVisible && detail"
      :url-list="[fileUrl]"
      @close="previewVisible = false"
      :hide-on-click-modal="true"
    />

    <!-- 添加到相册对话框 -->
    <el-dialog v-model="addToAlbumVisible" title="添加到相册" width="380px" append-to-body>
      <div v-if="albumsLoading" class="py-4">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="userAlbums.length === 0" class="py-4 text-center text-gray-400">
        还没有相册，请先在相册页面创建
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="album in userAlbums"
          :key="album.id"
          class="flex items-center justify-between px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer"
          @click="handleAddToAlbum(album)"
        >
          <div>
            <p class="text-sm font-medium">{{ album.name }}</p>
            <p class="text-xs text-gray-400">{{ album.photo_count }} 张照片</p>
          </div>
          <el-icon v-if="addedAlbumIds.has(album.id)" color="#67C23A" :size="18"><Check /></el-icon>
        </div>
      </div>
    </el-dialog>

    <!-- 重新分析对话框 -->
    <el-dialog v-model="reanalyzeVisible" title="重新分析" width="380px" append-to-body>
      <p class="text-xs text-gray-400 mb-3">选择需要重新执行的 AI 分析任务：</p>
      <el-checkbox-group v-model="reanalyzeTasks" class="flex flex-col gap-1">
        <el-checkbox
          v-for="opt in REANALYZE_TASK_OPTIONS"
          :key="opt.value"
          :value="opt.value"
          :label="opt.label"
        />
      </el-checkbox-group>
      <template #footer>
        <el-button size="small" @click="reanalyzeVisible = false">取消</el-button>
        <el-button
          type="primary"
          size="small"
          :loading="reanalyzeSubmitting"
          :disabled="reanalyzeTasks.length === 0"
          @click="handleReanalyze"
        >
          提交
        </el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { photoApi } from '@/api/photo'
import { albumApi } from '@/api/album'
import { REANALYZE_TASK_OPTIONS } from '@/types/task'
import type { PhotoDetail } from '@/types/photo'
import type { Album } from '@/types/album'

const props = defineProps<{
  visible: boolean
  photoId: string | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const drawerVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const loading = ref(false)
const detail = ref<PhotoDetail | null>(null)
const previewVisible = ref(false)

// ── 添加到相册 ─────────────
const addToAlbumVisible = ref(false)
const albumsLoading = ref(false)
const userAlbums = ref<Album[]>([])
const addedAlbumIds = ref<Set<string>>(new Set())

async function openAddToAlbumDialog() {
  addToAlbumVisible.value = true
  albumsLoading.value = true
  addedAlbumIds.value = new Set()
  try {
    const res = await albumApi.list()
    userAlbums.value = res.data.filter(a => !a.is_system)
  } catch {
    // handled by interceptor
  } finally {
    albumsLoading.value = false
  }
}

async function handleAddToAlbum(album: Album) {
  if (!detail.value) return
  try {
    await albumApi.addPhoto(album.id, detail.value.id)
    addedAlbumIds.value.add(album.id)
    ElMessage.success(`已添加到「${album.name}」`)
  } catch {
    // handled by interceptor
  }
}

// ── 重新分析 ─────────
const reanalyzeVisible = ref(false)
const reanalyzeSubmitting = ref(false)
const reanalyzeTasks = ref<string[]>([
  'image_description',
  'image_embedding',
  'quality_assessment',
])

function openReanalyzeDialog() {
  reanalyzeTasks.value = ['image_description', 'image_embedding', 'quality_assessment']
  reanalyzeVisible.value = true
}

async function handleReanalyze() {
  if (!detail.value || reanalyzeTasks.value.length === 0) return
  reanalyzeSubmitting.value = true
  try {
    const res = await photoApi.reanalyze(detail.value.id, reanalyzeTasks.value)
    reanalyzeVisible.value = false
    ElMessage.success(`已创建 ${res.data.tasks.length} 个分析任务，可在任务中心查看进度`)
  } catch {
    // handled by interceptor
  } finally {
    reanalyzeSubmitting.value = false
  }
}

const meta = computed(() => detail.value?.metadata)
const fileUrl = computed(() => (detail.value ? photoApi.fileUrl(detail.value.id) : ''))

const dimensions = computed(() => {
  if (detail.value?.width && detail.value?.height) {
    return `${detail.value.width} × ${detail.value.height}`
  }
  return '—'
})

const hasCameraInfo = computed(() => {
  const m = meta.value
  if (!m) return false
  return Boolean(
    m.camera_make ||
      m.camera_model ||
      m.lens_model ||
      m.focal_length ||
      m.aperture ||
      m.shutter_speed ||
      m.iso
  )
})

const hasDescription = computed(() => !!detail.value?.description?.description)
const hasNarrative = computed(() => !!detail.value?.description?.narrative)

const hasCoords = computed(() =>
  meta.value?.latitude != null && meta.value?.longitude != null
)

const locationText = computed(() => {
  const m = meta.value
  if (!m) return ''
  return [m.country, m.province, m.city, m.district].filter(Boolean).join(' ')
})

const hasLocation = computed(() => hasCoords.value || Boolean(locationText.value))

// ── AI 分析字段 ───────────────
const aiDesc = computed(() => detail.value?.description?.description || '')
const aiTags = computed<string[]>(() => {
  const tags = detail.value?.description?.tags
  if (Array.isArray(tags)) return tags
  if (typeof tags === 'string') {
    try { return JSON.parse(tags) } catch { return [] }
  }
  return []
})
const qualityScore = computed(() => detail.value?.description?.quality_score ?? null)
const memoryScore = computed(() => detail.value?.description?.memory_score ?? null)
const hasScores = computed(() => qualityScore.value != null || memoryScore.value != null)
const hasAiInfo = computed(() =>
  aiTags.value.length > 0 || Boolean(aiDesc.value) || hasScores.value
)

/** 字节转可读大小 */
function formatFileSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

/** 格式化时间 */
function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function fetchDetail(id: string) {
  loading.value = true
  detail.value = null
  try {
    const res = await photoApi.getById(id)
    detail.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.visible, props.photoId] as const,
  ([visible, id]) => {
    if (visible && id) {
      fetchDetail(id)
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.preview-box {
  @apply w-full rounded-lg overflow-hidden bg-gray-100 cursor-pointer;
}

.preview-img {
  @apply w-full max-h-60 object-contain bg-gray-50;
}
</style>
