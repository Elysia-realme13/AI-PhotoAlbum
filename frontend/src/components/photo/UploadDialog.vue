<template>
  <el-dialog
    :model-value="visible"
    title="上传照片"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-upload
      ref="uploadRef"
      v-model:file-list="fileList"
      drag
      multiple
      :auto-upload="false"
      :show-file-list="true"
      :before-upload="() => false"
      accept="image/*,.heic,.heif"
      class="upload-dialog"
    >
      <el-icon :size="48" color="#409EFF"><UploadFilled /></el-icon>
      <div class="mt-3 text-gray-600">拖拽照片到此处，或点击上传</div>
      <template #tip>
        <div class="text-xs text-gray-400 mt-1">支持 JPG、PNG、HEIC、GIF、WebP 等格式</div>
      </template>
    </el-upload>

    <!-- 上传进度 -->
    <div v-if="uploading" class="mt-4">
      <div class="flex items-center justify-between mb-1">
        <span class="text-sm text-gray-600">{{ uploadingFile?.name }}</span>
        <span class="text-sm text-gray-400">{{ progress }}%</span>
      </div>
      <el-progress :percentage="progress" :stroke-width="6" />
    </div>

    <template #footer>
      <el-button @click="close" :disabled="uploading">取消</el-button>
      <el-button type="primary" :loading="uploading" @click="startUpload">
        {{ uploading ? '上传中...' : '开始上传' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { UploadUserFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

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
const fileList = ref<UploadUserFile[]>([])

// 对话框打开且带有预填文件时（来自页面拖拽），填充文件列表
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.initialFiles && props.initialFiles.length > 0) {
      fileList.value = props.initialFiles.map((file, index) => ({
        name: file.name,
        raw: file as UploadUserFile['raw'],
        uid: Date.now() + index,
        status: 'ready' as const,
      }))
    }
  }
)

async function startUpload() {
  const files = fileList.value.map((f) => f.raw).filter(Boolean) as File[]
  if (files.length === 0) return

  uploading.value = true
  const { usePhotoStore } = await import('@/stores/photo')
  const store = usePhotoStore()

  for (const file of files) {
    uploadingFile.value = file
    progress.value = 0
    await store.uploadPhoto(file)
    progress.value = 100
  }

  uploading.value = false
  emit('uploaded')
  close()
}

function close() {
  fileList.value = []
  uploading.value = false
  progress.value = 0
  emit('update:visible', false)
}
</script>
