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
      drag
      multiple
      :auto-upload="false"
      :show-file-list="true"
      :on-change="handleFileChange"
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
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  uploaded: []
}>()

const uploadRef = ref()
const uploading = ref(false)
const progress = ref(0)
const uploadingFile = ref<File | null>(null)
const fileQueue = ref<File[]>([])

function handleFileChange(_file: any, fileList: any[]) {
  fileQueue.value = fileList.map((f: any) => f.raw).filter(Boolean)
}

async function startUpload() {
  if (fileQueue.value.length === 0) return

  uploading.value = true
  const { usePhotoStore } = await import('@/stores/photo')
  const store = usePhotoStore()

  for (const file of fileQueue.value) {
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
  fileQueue.value = []
  uploading.value = false
  progress.value = 0
  emit('update:visible', false)
}
</script>
