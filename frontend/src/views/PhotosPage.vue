<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-gray-800">照片</h2>
      <el-button type="primary" :icon="Upload" @click="showUpload = true">上传照片</el-button>
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUpload" title="上传照片" width="500px">
      <el-upload
        drag
        multiple
        :auto-upload="false"
        :on-change="handleFileChange"
        accept="image/*,.heic,.heif"
      >
        <el-icon :size="48" color="#409EFF"><UploadFilled /></el-icon>
        <div class="mt-3 text-gray-600">拖拽照片到此处，或点击上传</div>
        <template #tip>
          <div class="text-xs text-gray-400 mt-1">支持 JPG、PNG、HEIC、GIF 等格式</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" @click="showUpload = false">开始上传</el-button>
      </template>
    </el-dialog>

    <!-- 照片列表（占位） -->
    <el-empty description="功能开发中，敬请期待..." />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Upload, UploadFilled } from '@element-plus/icons-vue'

const showUpload = ref(false)

function handleFileChange() {
  // TODO: Phase 2
}
</script>
