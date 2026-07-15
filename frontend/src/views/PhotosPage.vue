<template>
  <div>
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
    <UploadDialog v-model:visible="showUpload" @uploaded="onUploaded" />

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewList"
      :initial-index="previewIndex"
      @close="previewVisible = false"
      :hide-on-click-modal="true"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { usePhotoStore } from '@/stores/photo'
import { photoApi } from '@/api/photo'
import PhotoGrid from '@/components/photo/PhotoGrid.vue'
import UploadDialog from '@/components/photo/UploadDialog.vue'
import type { PhotoItem } from '@/types/photo'

const store = usePhotoStore()

const showUpload = ref(false)

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

onMounted(() => {
  store.fetchPhotos()
})
</script>
