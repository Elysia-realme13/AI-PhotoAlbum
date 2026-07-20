<template>
  <div>
    <!-- 人物列表视图 -->
    <template v-if="view === 'list'">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">人物</h2>
        <div class="flex items-center gap-3">
          <el-input
            v-model="searchQuery"
            placeholder="搜索人物…"
            clearable
            :prefix-icon="Search"
            size="small"
            class="w-52"
            @input="onSearchInput"
            @clear="onSearchClear"
          />
          <template v-if="mergeMode">
            <span class="text-sm text-gray-500 dark:text-dark-text-secondary">已选 {{ selectedIds.size }} 个</span>
            <el-button
              type="primary"
              :disabled="selectedIds.size < 2"
              :loading="merging"
              @click="openMergeDialog"
            >
              合并
            </el-button>
            <el-button @click="exitMergeMode">退出</el-button>
          </template>
          <template v-else>
            <p class="text-sm text-gray-400 dark:text-dark-text-secondary">系统自动识别照片中的人脸并聚类</p>
            <el-button :disabled="identities.length < 2" @click="enterMergeMode">合并人物</el-button>
            <el-button size="small" @click="handleCleanup">清理空聚类</el-button>
          </template>
        </div>
      </div>

      <!-- 加载骨架屏 -->
      <div v-if="loading" class="grid grid-cols-4 gap-4">
        <div v-for="i in 8" :key="i" class="bg-white dark:bg-dark-card rounded-xl p-4 shadow-sm border border-gray-100 dark:border-dark-border flex flex-col items-center">
          <div class="w-20 h-20 rounded-full bg-gray-200 dark:bg-dark-hover animate-pulse mb-3" />
          <div class="h-4 bg-gray-200 dark:bg-dark-hover rounded w-16 mb-2 animate-pulse" />
          <div class="h-3 bg-gray-200 dark:bg-dark-hover rounded w-10 animate-pulse" />
        </div>
      </div>

      <template v-else>
        <el-empty v-if="identities.length === 0" description="还没有识别到人物，上传照片后系统会自动识别" />
        <div v-else class="grid grid-cols-4 gap-4">
          <div
            v-for="person in identities"
            :key="person.identity_id"
            class="group relative bg-white dark:bg-dark-card rounded-xl p-4 shadow-sm border cursor-pointer hover:shadow-md transition-shadow flex flex-col items-center"
            :class="mergeMode && selectedIds.has(person.identity_id)
              ? 'border-blue-500 ring-2 ring-blue-500/40'
              : 'border-gray-100 dark:border-dark-border'"
            @click="onCardClick(person)"
          >
            <!-- 多选勾选标记 -->
            <div
              v-if="mergeMode"
              class="absolute top-2 left-2 w-5 h-5 rounded-full border-2 flex items-center justify-center"
              :class="selectedIds.has(person.identity_id)
                ? 'bg-blue-500 border-blue-500 text-white'
                : 'bg-white/80 border-gray-300'"
            >
              <el-icon v-if="selectedIds.has(person.identity_id)" :size="12"><Check /></el-icon>
            </div>
            <!-- 圆形头像 -->
            <div class="w-20 h-20 rounded-full overflow-hidden bg-blue-500 text-white flex items-center justify-center text-2xl font-bold mb-3">
              <img
                v-if="person.cover_photo_id"
                :src="photoApi.thumbnailUrl(person.cover_photo_id)"
                class="w-full h-full object-cover"
              />
              <span v-else>{{ personInitial(person) }}</span>
            </div>
            <p class="text-sm font-medium text-gray-800 dark:text-dark-text truncate max-w-full">
              {{ person.identity_name || '未命名' }}
            </p>
            <p class="text-xs text-gray-400 dark:text-dark-text-secondary mt-0.5">{{ person.face_count }} 张照片</p>

            <!-- hover 重命名按钮（合并模式下隐藏） -->
            <button
              v-if="!mergeMode"
              class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500"
              @click.stop="renamePerson(person)"
              title="重命名"
            >
              <el-icon :size="14"><EditPen /></el-icon>
            </button>
          </div>
        </div>
      </template>
    </template>

    <!-- 人物详情视图 -->
    <template v-else>
      <div class="flex items-center gap-3 mb-6">
        <el-button :icon="ArrowLeft" circle @click="backToList" aria-label="返回人物列表" />
        <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">{{ currentPerson?.identity_name || '未命名' }}</h2>
        <button
          class="w-7 h-7 rounded-full hover:bg-gray-100 dark:hover:bg-dark-hover flex items-center justify-center text-gray-400 hover:text-blue-500 dark:text-dark-text-secondary"
          @click="currentPerson && renamePerson(currentPerson)"
          title="重命名"
        >
          <el-icon :size="16"><EditPen /></el-icon>
        </button>
        <span class="text-sm text-gray-400 dark:text-dark-text-secondary">{{ currentPhotos.length }} 张</span>
      </div>

      <div v-if="detailLoading" class="grid grid-cols-6 gap-3">
        <div v-for="i in 12" :key="i" class="aspect-square bg-gray-200 dark:bg-dark-hover rounded-lg animate-pulse" />
      </div>
      <div v-else class="grid grid-cols-6 gap-3">
        <div
          v-for="(photo, index) in currentPhotos"
          :key="photo.id"
          class="group relative aspect-square bg-gray-100 dark:bg-dark-hover rounded-lg overflow-hidden cursor-pointer"
          @click="handlePreview(index)"
        >
          <img
            :src="photoApi.thumbnailUrl(photo.id)"
            class="w-full h-full object-cover group-hover:opacity-80 transition-opacity"
          />
          <button
            class="absolute top-1 right-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500"
            @click.stop="handleDetail(photo)"
            title="详情"
          >
            <el-icon :size="14"><InfoFilled /></el-icon>
          </button>
        </div>
      </div>
    </template>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewList"
      :initial-index="previewIndex"
      @close="previewVisible = false"
      :hide-on-click-modal="true"
    />

    <!-- 详情抽屉 -->
    <PhotoDetailDrawer v-model:visible="detailVisible" :photo-id="detailPhotoId" />

    <!-- 合并确认对话框：选择保留的目标人物 -->
    <el-dialog v-model="mergeDialogVisible" title="合并人物" width="420px">
      <p class="text-sm text-gray-500 dark:text-dark-text-secondary mb-3">
        选择保留的人物，其余选中的人物将合并到它名下（不可撤销）。
      </p>
      <el-radio-group v-model="mergeTargetId" class="flex flex-col gap-2">
        <el-radio
          v-for="person in selectedPersons"
          :key="person.identity_id"
          :value="person.identity_id"
        >
          {{ person.identity_name || '未命名' }}
          <span class="text-xs text-gray-400">({{ person.face_count }} 张)</span>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="mergeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="merging" :disabled="!mergeTargetId" @click="confirmMerge">
          确认合并
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, InfoFilled, EditPen, Check, Search } from '@element-plus/icons-vue'
import { photoApi } from '@/api/photo'
import { faceApi } from '@/api/face'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'
import type { FaceCluster } from '@/types/face'

// ── 状态 ─────────────────────────
const loading = ref(true)
const identities = ref<FaceCluster[]>([])
const searchQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const view = ref<'list' | 'detail'>('list')
const currentPerson = ref<FaceCluster | null>(null)
const currentPhotos = ref<PhotoItem[]>([])
const detailLoading = ref(false)

// ── 工具 ─────────────────────────
function personInitial(person: FaceCluster): string {
  const name = person.identity_name || '?'
  return name.charAt(0).toUpperCase()
}

// ── 列表数据 ─────────────────────────
async function fetchIdentities(q?: string) {
  loading.value = true
  try {
    const res = await faceApi.listIdentities(q || undefined)
    identities.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

// ── 搜索 ─────────────────────────
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchIdentities(searchQuery.value.trim() || undefined)
  }, 300)
}

function onSearchClear() {
  searchQuery.value = ''
  fetchIdentities()
}

// ── 详情：加载某人物的照片 ─────────────────
async function openPerson(person: FaceCluster) {
  currentPerson.value = person
  view.value = 'detail'
  detailLoading.value = true
  try {
    const res = await faceApi.identityPhotos(person.identity_id)
    currentPhotos.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    detailLoading.value = false
  }
}

function backToList() {
  view.value = 'list'
  currentPerson.value = null
  currentPhotos.value = []
}

// ── 重命名 ─────────────────────────
async function renamePerson(person: FaceCluster) {
  try {
    const { value } = await ElMessageBox.prompt('请输入人物名称', '重命名', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: person.identity_name || '',
      inputValidator: (v: string) => (v && v.trim().length > 0 ? true : '名称不能为空'),
    })
    const newName = value.trim()
    await faceApi.renameCluster(person.identity_id, newName)
    // 同步更新本地状态
    person.identity_name = newName
    const target = identities.value.find((p) => p.identity_id === person.identity_id)
    if (target) target.identity_name = newName
    if (currentPerson.value?.identity_id === person.identity_id) currentPerson.value.identity_name = newName
    ElMessage.success('已重命名')
  } catch {
    // 用户取消或请求失败
  }
}

// ── 多选合并 ──────────────────
const mergeMode = ref(false)
const selectedIds = ref(new Set<string>())
const merging = ref(false)
const mergeDialogVisible = ref(false)
const mergeTargetId = ref('')

const selectedPersons = computed(() =>
  identities.value.filter((p) => selectedIds.value.has(p.identity_id))
)

function enterMergeMode() {
  mergeMode.value = true
  selectedIds.value = new Set()
}

function exitMergeMode() {
  mergeMode.value = false
  selectedIds.value = new Set()
}

function onCardClick(person: FaceCluster) {
  if (mergeMode.value) {
    toggleSelect(person.identity_id)
  } else {
    openPerson(person)
  }
}

function toggleSelect(id: string) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  // 触发响应式更新
  selectedIds.value = new Set(selectedIds.value)
}

function openMergeDialog() {
  if (selectedIds.value.size < 2) return
  // 默认目标：选中中照片最多、且已命名优先
  const sorted = [...selectedPersons.value].sort((a, b) => {
    const an = a.identity_name ? 1 : 0
    const bn = b.identity_name ? 1 : 0
    if (an !== bn) return bn - an
    return b.face_count - a.face_count
  })
  mergeTargetId.value = sorted[0]?.identity_id || ''
  mergeDialogVisible.value = true
}

async function confirmMerge() {
  const targetId = mergeTargetId.value
  if (!targetId) return
  const sourceIds = [...selectedIds.value].filter((id) => id !== targetId)
  if (sourceIds.length === 0) return

  merging.value = true
  try {
    await faceApi.mergeClustersBatch(sourceIds, targetId)
    ElMessage.success(`已合并 ${sourceIds.length} 个人物`)
    mergeDialogVisible.value = false
    exitMergeMode()
    await fetchIdentities()
  } catch {
    ElMessage.error('合并失败，请重试')
  } finally {
    merging.value = false
  }
}

    async function handleCleanup() {
      try {
        const res = await faceApi.cleanupEmpty()
        ElMessage.success('已清理 ' + res.data.deleted + ' 个空聚类')
        fetchIdentities(searchQuery.value.trim() || undefined)
      } catch {
        // handled by interceptor
      }
    }

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() => currentPhotos.value.map((p) => photoApi.fileUrl(p.id)))

function handlePreview(index: number) {
  previewIndex.value = index
  previewVisible.value = true
}

// ── 详情抽屉 ─────────────────────────
const detailVisible = ref(false)
const detailPhotoId = ref<string | null>(null)

function handleDetail(photo: PhotoItem) {
  detailPhotoId.value = photo.id
  detailVisible.value = true
}

// ── 初始化 ─────────────────────────
onMounted(fetchIdentities)
</script>
