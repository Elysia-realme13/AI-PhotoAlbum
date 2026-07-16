<template>
  <el-dialog
    :model-value="visible"
    title="上传照片"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <!-- 包装层：阻止拖拽事件冒泡到页面 + 自定义文件夹拖拽支持 -->
    <div
      @dragenter.stop
      @dragover.stop.prevent="onDialogDragOver"
      @dragleave.stop
      @drop.stop.prevent="onDialogDrop"
    >
      <el-upload
        ref="uploadRef"
        multiple
        :auto-upload="false"
        :show-file-list="true"
        :file-list="displayList"
        :before-upload="() => false"
        :on-change="handleChange"
        :on-remove="handleRemove"
        accept="image/*,.heic,.heif"
        class="upload-dialog"
      >
        <el-icon :size="48" color="#409EFF"><UploadFilled /></el-icon>
        <div class="mt-3 text-gray-600 dark:text-dark-text-secondary">
          {{ isDropActive ? '松开鼠标即可上传' : '拖拽照片到此处，或点击选择' }}
        </div>
        <template #tip>
          <div class="text-xs text-gray-400 mt-1">支持 JPG、PNG、HEIC、GIF、WebP 等格式，可拖入含图片的文件夹</div>
        </template>
      </el-upload>
    </div>

    <!-- 上传进度 -->
    <div v-if="uploading" class="mt-4">
      <div class="flex items-center justify-between mb-1">
        <span class="text-sm text-gray-600 dark:text-dark-text-secondary">{{ uploadingFile?.name }}</span>
        <span class="text-sm text-gray-400">{{ progress }}%</span>
      </div>
      <el-progress :percentage="progress" :stroke-width="6" />
    </div>

    <template #footer>
      <el-button @click="close" :disabled="uploading">取消</el-button>
      <el-button type="primary" :loading="uploading" :disabled="rawFiles.length === 0" @click="startUpload">
        {{ uploading ? '上传中...' : `开始上传 (${rawFiles.length})` }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadUserFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { extractImagesFromDrop } from '@/utils/dropFiles'

const props = defineProps<{
  visible: boolean
  initialFiles?: File[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  uploaded: []
}>()

const uploadRef = ref()
const uploading = ref(false)
const progress = ref(0)
const uploadingFile = ref<File | null>(null)
const isDropActive = ref(false)

// 直接保存原始 File 对象引用，避免 el-upload 内部修改导致丢失
const rawFiles = ref<File[]>([])
// el-upload 显示列表（仅用于 UI 展示）
const displayList = ref<UploadUserFile[]>([])

// 对话框打开且带有预填文件时（来自页面拖拽），直接保存原始 File 引用
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.initialFiles && props.initialFiles.length > 0) {
      rawFiles.value = [...props.initialFiles]
      displayList.value = props.initialFiles.map((file, index) => ({
        name: file.name,
        uid: Date.now() + index,
        status: 'ready' as const,
      }))
    } else if (visible) {
      rawFiles.value = []
      displayList.value = []
    }
  }
)

// ── 对话框内拖拽状态 ─────────────────────────
function onDialogDragOver(e: DragEvent) {
  isDropActive.value = true
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

// ── 对话框内 drop：支持文件夹递归提取 ─────────────────────────
async function onDialogDrop(e: DragEvent) {
  isDropActive.value = false
  if (!e.dataTransfer) return

  const { images, skipped } = await extractImagesFromDrop(e.dataTransfer)

  for (const file of images) {
    addRawFile(file)
  }
  if (skipped > 0) {
    ElMessage.info(`已跳过 ${skipped} 个非图片文件`)
  }
  if (images.length === 0 && skipped === 0) {
    ElMessage.warning('未找到可上传的图片')
  }
}

// ── 将原始 File 对象加入列表（去重） ─────────────────────────
function addRawFile(file: File) {
  if (rawFiles.value.some(f => f.name === file.name && f.size === file.size)) return
  rawFiles.value.push(file)
  displayList.value.push({
    name: file.name,
    uid: Date.now() + Math.random(),
    status: 'ready' as const,
  })
}

// el-upload 文件变更回调（用户通过点击/文件选择器添加文件）
function handleChange(file: UploadFile) {
  if (file.raw && !rawFiles.value.some(f => f.name === file.name && f.size === file.raw!.size)) {
    rawFiles.value.push(file.raw)
  }
}

// el-upload 文件移除回调
function handleRemove(file: UploadFile) {
  const idx = displayList.value.findIndex(f => f.uid === file.uid)
  if (idx >= 0 && idx < rawFiles.value.length) {
    rawFiles.value.splice(idx, 1)
  }
}

async function startUpload() {
  const files = rawFiles.value.filter(f => f instanceof File && f.size > 0)
  if (files.length === 0) {
    ElMessage.warning('请先选择要上传的照片')
    return
  }

  uploading.value = true
  const { usePhotoStore } = await import('@/stores/photo')
  const store = usePhotoStore()

  let successCount = 0
  let failCount = 0
  for (const file of files) {
    uploadingFile.value = file
    progress.value = 0
    try {
      const result = await store.uploadPhoto(file)
      if (result) {
        successCount++
      } else {
        failCount++
      }
    } catch (e) {
      console.error('[UploadDialog] 上传异常:', file.name, e)
      failCount++
    }
    progress.value = 100
  }

  uploading.value = false
  if (successCount > 0 && failCount === 0) {
    ElMessage.success(`成功上传 ${successCount} 张照片`)
  } else if (successCount > 0 && failCount > 0) {
    ElMessage.warning(`上传完成：${successCount} 张成功，${failCount} 张失败`)
  } else if (failCount > 0) {
    ElMessage.error('上传失败，请检查网络连接')
  }
  emit('uploaded')
  close()
}

function close() {
  rawFiles.value = []
  displayList.value = []
  uploading.value = false
  progress.value = 0
  isDropActive.value = false
  emit('update:visible', false)
}
</script>
