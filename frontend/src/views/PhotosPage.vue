<template>
  <div
    class="relative"
    @dragenter.prevent="handleDragEnter"
    @dragover.prevent="handleDragOver"
    @dragleave.prevent="handleDragLeave"
    @drop.prevent="handleDrop"
  >
    <!-- 顶部操作栏 -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">照片</h2>
      <div class="flex items-center gap-2">
        <!-- 视图切换（非选择模式） -->
        <el-segmented
          v-if="!isSelectMode"
          v-model="viewMode"
          :options="viewOptions"
          size="small"
        />
        <!-- 选择模式下的操作按钮 -->
        <template v-if="isSelectMode">
          <span class="text-sm text-gray-500 dark:text-dark-text-secondary">已选 {{ selectedIds.size }} 张</span>
          <el-button :disabled="selectedIds.size === 0" @click="selectAll">全选</el-button>
          <el-button :disabled="selectedIds.size === 0" @click="selectedIds.clear()">取消</el-button>
          <el-button type="danger" :disabled="selectedIds.size === 0" :loading="batchDeleting" @click="handleBatchDelete">
            删除选中
          </el-button>
          <el-button @click="exitSelectMode">退出选择</el-button>
        </template>
        <!-- 普通模式 -->
        <template v-else>
          <el-button :icon="Check" @click="enterSelectMode">批量选择</el-button>
          <el-button type="primary" :icon="Upload" @click="showUpload = true">上传照片</el-button>
        </template>
      </div>
    </div>

    <!-- 照片网格 -->
    <PhotoGrid
      v-if="viewMode === 'grid'"
      :photos="store.photos"
      :loading="store.loading"
      :selectable="isSelectMode"
      :selected-ids="selectedIds"
      @upload="showUpload = true"
      @preview="handlePreview"
      @detail="handleDetail"
      @delete="handleDelete"
      @select="handleSelect"
    />

    <!-- 时间线视图 -->
    <PhotoTimeline v-else @detail="handleDetailId" />

    <!-- 分页（仅网格视图） -->
    <div v-if="viewMode === 'grid' && store.total > store.pageSize" class="flex justify-center mt-6">
      <el-pagination
        v-model:current-page="store.currentPage"
        :page-size="store.pageSize"
        :total="store.total"
        layout="prev, pager, next"
        background
        @current-change="store.fetchPhotos"
      />
    </div>

    <!-- 上传对话框 -->
    <UploadDialog
      v-model:visible="showUpload"
      :initial-files="pendingFiles"
      @uploaded="onUploaded"
      @update:visible="onDialogVisibleChange"
    />

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

    <!-- 拖拽上传遮罩 -->
    <div
      v-if="isDragging"
      class="fixed inset-0 z-50 bg-blue-500/10 backdrop-blur-sm flex items-center justify-center pointer-events-none"
    >
      <div class="bg-white dark:bg-dark-card rounded-2xl shadow-lg px-10 py-8 text-center border-2 border-dashed border-blue-400">
        <el-icon :size="56" color="#409EFF" class="mb-3"><UploadFilled /></el-icon>
        <p class="text-lg font-semibold text-gray-800 dark:text-dark-text">松开鼠标上传照片</p>
        <p class="text-sm text-gray-400 dark:text-dark-text-secondary mt-1">支持拖入图片或含图片的文件夹</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled, Check } from '@element-plus/icons-vue'
import { usePhotoStore } from '@/stores/photo'
import { photoApi } from '@/api/photo'
import { extractImagesFromDrop } from '@/utils/dropFiles'
import PhotoGrid from '@/components/photo/PhotoGrid.vue'
import UploadDialog from '@/components/photo/UploadDialog.vue'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import PhotoTimeline from '@/components/photo/PhotoTimeline.vue'
import type { PhotoItem } from '@/types/photo'

const store = usePhotoStore()

// ── 视图模式：网格 / 时间线 ─────
const viewMode = ref<'grid' | 'timeline'>('grid')
const viewOptions = [
  { label: '网格', value: 'grid' },
  { label: '时间线', value: 'timeline' },
]

const showUpload = ref(false)
const pendingFiles = ref<File[]>([])

// ── 批量选择 ─────────────────────────
const isSelectMode = ref(false)
const selectedIds = ref(new Set<string>())
const batchDeleting = ref(false)

function enterSelectMode() {
  isSelectMode.value = true
  selectedIds.value.clear()
}

function exitSelectMode() {
  isSelectMode.value = false
  selectedIds.value.clear()
}

function selectAll() {
  store.photos.forEach(p => selectedIds.value.add(p.id))
  // 触发响应式更新
  selectedIds.value = new Set(selectedIds.value)
}

function handleSelect(id: string) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  // 触发响应式更新
  selectedIds.value = new Set(selectedIds.value)
}

async function handleBatchDelete() {
  const count = selectedIds.value.size
  if (count === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${count} 张照片吗？删除后可在回收站恢复。`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  batchDeleting.value = true
  const ids = [...selectedIds.value]

  try {
    const res = await photoApi.batchDelete(ids)
    const { success_count, fail_count } = res.data
    
    // 刷新列表
    await store.fetchPhotos()

    if (success_count > 0 && fail_count === 0) {
      ElMessage.success(`成功删除 ${success_count} 张照片`)
    } else if (success_count > 0 && fail_count > 0) {
      ElMessage.warning(`删除完成：${success_count} 张成功，${fail_count} 张失败`)
    } else {
      ElMessage.error('删除失败，请重试')
    }
  } catch {
    ElMessage.error('删除失败，请重试')
  } finally {
    batchDeleting.value = false
  }

  exitSelectMode()
}

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() =>
  store.photos.map((p) => photoApi.fileUrl(p.id))
)

function handlePreview(photo: PhotoItem) {
  previewIndex.value = store.photos.findIndex((p) => p.id === photo.id)
  previewVisible.value = true
}

// ── 详情抽屉 ─────────────────
const detailVisible = ref(false)
const detailPhotoId = ref<string | null>(null)

function handleDetail(photo: PhotoItem) {
  detailPhotoId.value = photo.id
  detailVisible.value = true
}

function handleDetailId(id: string) {
  detailPhotoId.value = id
  detailVisible.value = true
}

// ── 删除确认 ─────────────────────────
function handleDelete(photo: PhotoItem) {
  ElMessageBox.confirm(
    `确定要删除照片 "${photo.original_name || photo.filename}" 吗？`,
    '确认删除',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  ).then(() => {
    store.removePhoto(photo.id)
  }).catch(() => {
    // 取消
  })
}

function onUploaded() {
  store.fetchPhotos(1)
}

// ── 拖拽上传 ───────────────────
const isDragging = ref(false)
let dragCounter = 0

function hasFiles(e: DragEvent): boolean {
  return !!e.dataTransfer && Array.from(e.dataTransfer.types).includes('Files')
}

function handleDragEnter(e: DragEvent) {
  if (!hasFiles(e)) return
  // 忽略来自上传对话框内部的拖拽事件
  if ((e.target as HTMLElement)?.closest?.('.el-dialog')) return
  dragCounter++
  isDragging.value = true
}

function handleDragOver(e: DragEvent) {
  if (!hasFiles(e)) return
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function handleDragLeave(e: DragEvent) {
  if (!hasFiles(e)) return
  if ((e.target as HTMLElement)?.closest?.('.el-dialog')) return
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragging.value = false
  }
}

async function handleDrop(e: DragEvent) {
  dragCounter = 0
  isDragging.value = false
  if (!e.dataTransfer) return

  // 忽略来自对话框内部的 drop 事件（避免 el-upload 拖拽区冒泡）
  const uploadDialog = (e.target as HTMLElement)?.closest?.('.el-dialog')
  if (uploadDialog) return

  const { images, skipped } = await extractImagesFromDrop(e.dataTransfer)

  if (images.length === 0) {
    ElMessage.warning('未找到可上传的图片')
    return
  }
  if (skipped > 0) {
    ElMessage.info(`已跳过 ${skipped} 个非图片文件`)
  }

  pendingFiles.value = images
  showUpload.value = true
}

function onDialogVisibleChange(visible: boolean) {
  if (!visible) pendingFiles.value = []
}

onMounted(() => {
  store.fetchPhotos()
})
</script>
