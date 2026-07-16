<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">回收站</h2>
      <div class="flex items-center gap-2">
        <!-- 选择模式下的操作按钮 -->
        <template v-if="isSelectMode">
          <span class="text-sm text-gray-500 dark:text-dark-text-secondary">已选 {{ selectedIds.size }} 张</span>
          <el-button :disabled="selectedIds.size === 0" @click="selectAll">全选</el-button>
          <el-button :disabled="selectedIds.size === 0" @click="selectedIds.clear()">取消</el-button>
          <el-button type="primary" :disabled="selectedIds.size === 0" :loading="batchRestoring" @click="handleBatchRestore">
            批量恢复
          </el-button>
          <el-button type="danger" :disabled="selectedIds.size === 0" :loading="batchDeleting" @click="handleBatchPermanentDelete">
            彻底删除
          </el-button>
          <el-button @click="exitSelectMode">退出选择</el-button>
        </template>
        <!-- 普通模式 -->
        <template v-else>
          <el-button :icon="Check" @click="enterSelectMode" :disabled="photos.length === 0">批量选择</el-button>
          <el-button type="danger" @click="handleEmptyRecycleBin" :disabled="photos.length === 0">清空回收站</el-button>
        </template>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      <div v-for="i in 6" :key="i" class="aspect-square rounded-lg bg-gray-200 dark:bg-dark-hover animate-pulse" />
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="photos.length === 0" description="回收站是空的" />

    <!-- 已删除照片网格 -->
    <PhotoGrid
      v-else
      :photos="photos"
      :loading="false"
      :selectable="isSelectMode"
      :selected-ids="selectedIds"
      recycle-mode
      @preview="handlePreview"
      @select="handleSelect"
      @restore="handleSingleRestore"
      @delete="handleSingleDelete"
    />

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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { photoApi } from '@/api/photo'
import PhotoGrid from '@/components/photo/PhotoGrid.vue'
import type { PhotoItem } from '@/types/photo'

const photos = ref<PhotoItem[]>([])
const loading = ref(false)

// ── 批量选择 ─────────────────────────
const isSelectMode = ref(false)
const selectedIds = ref(new Set<string>())
const batchRestoring = ref(false)
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
  photos.value.forEach(p => selectedIds.value.add(p.id))
  selectedIds.value = new Set(selectedIds.value)
}

function handleSelect(id: string) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  selectedIds.value = new Set(selectedIds.value)
}

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() =>
  photos.value.map((p) => photoApi.fileUrl(p.id))
)

function handlePreview(photo: PhotoItem) {
  previewIndex.value = photos.value.findIndex((p) => p.id === photo.id)
  previewVisible.value = true
}

// ── 单张恢复 ─────────────────────────
async function handleSingleRestore(photo: PhotoItem) {
  try {
    await photoApi.restore(photo.id)
    ElMessage.success('已恢复')
    await fetchRecycleBin()
  } catch {
    ElMessage.error('恢复失败')
  }
}

// ── 单张彻底删除 ─────────────────────────
async function handleSingleDelete(photo: PhotoItem) {
  try {
    await ElMessageBox.confirm(
      '确定要彻底删除这张照片吗？此操作不可恢复！',
      '彻底删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await photoApi.permanentDelete(photo.id)
    ElMessage.success('已彻底删除')
    await fetchRecycleBin()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ── 数据加载 ─────────────────────────
async function fetchRecycleBin() {
  loading.value = true
  try {
    const res = await photoApi.list({ is_deleted: true })
    photos.value = res.data.items || []
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

// ── 批量恢复 ─────────────────────────
async function handleBatchRestore() {
  const count = selectedIds.value.size
  if (count === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要恢复选中的 ${count} 张照片吗？`,
      '批量恢复',
      { confirmButtonText: '恢复', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }

  batchRestoring.value = true
  const ids = [...selectedIds.value]

  try {
    const res = await photoApi.batchRestore(ids)
    const { success_count, fail_count } = res.data

    await fetchRecycleBin()

    if (success_count > 0 && fail_count === 0) {
      ElMessage.success(`成功恢复 ${success_count} 张照片`)
    } else if (success_count > 0 && fail_count > 0) {
      ElMessage.warning(`恢复完成：${success_count} 张成功，${fail_count} 张失败`)
    } else {
      ElMessage.error('恢复失败，请重试')
    }
  } catch {
    ElMessage.error('恢复失败，请重试')
  } finally {
    batchRestoring.value = false
  }

  exitSelectMode()
}

// ── 批量永久删除 ─────────────────────────
async function handleBatchPermanentDelete() {
  const count = selectedIds.value.size
  if (count === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要彻底删除选中的 ${count} 张照片吗？此操作不可恢复！`,
      '批量彻底删除',
      { confirmButtonText: '彻底删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  batchDeleting.value = true
  const ids = [...selectedIds.value]

  try {
    const res = await photoApi.batchPermanentDelete(ids)
    const { success_count, fail_count } = res.data

    await fetchRecycleBin()

    if (success_count > 0 && fail_count === 0) {
      ElMessage.success(`成功彻底删除 ${success_count} 张照片`)
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

// ── 清空回收站 ─────────────────────────
async function handleEmptyRecycleBin() {
  try {
    await ElMessageBox.confirm(
      '确定要清空回收站吗？所有照片将被彻底删除，此操作不可恢复！',
      '清空回收站',
      { confirmButtonText: '清空', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  try {
    const res = await photoApi.batchPermanentDelete(photos.value.map(p => p.id))
    const { success_count } = res.data
    ElMessage.success(`已清空回收站，共删除 ${success_count} 张照片`)
    await fetchRecycleBin()
  } catch {
    ElMessage.error('清空失败，请重试')
  }
}

onMounted(fetchRecycleBin)
</script>
