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
      <h2 class="text-2xl font-bold text-gray-800">照片</h2>
      <el-button type="primary" :icon="Upload" @click="showUpload = true">
        上传照片
      </el-button>
    </div>

    <!-- 照片网格 -->
    <PhotoGrid
      :photos="store.photos"
      :loading="store.loading"
      @upload="showUpload = true"
      @preview="handlePreview"
      @detail="handleDetail"
      @delete="handleDelete"
    />

    <!-- 分页 -->
    <div v-if="store.total > store.pageSize" class="flex justify-center mt-6">
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
      <div class="bg-white rounded-2xl shadow-lg px-10 py-8 text-center border-2 border-dashed border-blue-400">
        <el-icon :size="56" color="#409EFF" class="mb-3"><UploadFilled /></el-icon>
        <p class="text-lg font-semibold text-gray-800">松开鼠标上传照片</p>
        <p class="text-sm text-gray-400 mt-1">支持拖入图片或含图片的文件夹</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled } from '@element-plus/icons-vue'
import { usePhotoStore } from '@/stores/photo'
import { photoApi } from '@/api/photo'
import { extractImagesFromDrop } from '@/utils/dropFiles'
import PhotoGrid from '@/components/photo/PhotoGrid.vue'
import UploadDialog from '@/components/photo/UploadDialog.vue'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'

const store = usePhotoStore()

const showUpload = ref(false)
const pendingFiles = ref<File[]>([])

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
  dragCounter++
  isDragging.value = true
}

function handleDragOver(e: DragEvent) {
  if (!hasFiles(e)) return
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function handleDragLeave(e: DragEvent) {
  if (!hasFiles(e)) return
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
