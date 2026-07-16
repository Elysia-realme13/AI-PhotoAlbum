<template>
  <div>
    <!-- 相册列表视图 -->
    <template v-if="view === 'list'">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800">相册</h2>
        <el-button type="primary" @click="openCreateDialog">
          创建相册
        </el-button>
      </div>

      <!-- 加载骨架屏 -->
      <div v-if="loading" class="grid grid-cols-4 gap-4">
        <div v-for="i in 8" :key="i" class="bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100">
          <div class="aspect-square bg-gray-200 animate-pulse" />
          <div class="p-3">
            <div class="h-4 bg-gray-200 rounded w-20 mb-2 animate-pulse" />
            <div class="h-3 bg-gray-200 rounded w-12 animate-pulse" />
          </div>
        </div>
      </div>

      <template v-else>
        <el-empty v-if="albums.length === 0" description="还没有相册，点击【创建相册】开始整理照片吧！" />
        <div v-else class="grid grid-cols-4 gap-4">
          <div
            v-for="album in albums"
            :key="album.id"
            class="group bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100 cursor-pointer hover:shadow-md transition-shadow relative"
            @click="openAlbum(album)"
          >
            <div class="relative aspect-square bg-gray-100 overflow-hidden">
              <img
                v-if="album.cover_photo_id"
                :src="photoApi.thumbnailUrl(album.cover_photo_id)"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform"
              />
              <div v-else class="w-full h-full flex items-center justify-center text-gray-300">
                <el-icon :size="48"><PictureFilled /></el-icon>
              </div>
              <span class="absolute bottom-2 right-2 px-2 py-0.5 rounded-full bg-black/50 text-white text-xs">
                {{ album.photo_count }} 张
              </span>
            </div>
            <div class="p-3">
              <p class="text-sm font-medium text-gray-800 truncate">{{ album.name }}</p>
              <p class="text-xs text-gray-400 mt-0.5">
                {{ album.description || '无描述' }}
              </p>
            </div>
            <!-- 操作按钮 -->
            <div class="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                class="w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-blue-500"
                @click.stop="openEditDialog(album)"
                title="编辑"
              >
                <el-icon :size="14"><Edit /></el-icon>
              </button>
              <button
                v-if="!album.is_system"
                class="w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-red-500"
                @click.stop="confirmDeleteAlbum(album)"
                title="删除相册"
              >
                <el-icon :size="16"><Delete /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- 相册详情视图 -->
    <template v-else>
      <div class="flex items-center gap-3 mb-6">
        <el-button :icon="ArrowLeft" circle @click="backToList" aria-label="返回相册列表" />
        <h2 class="text-2xl font-bold text-gray-800">{{ currentAlbum?.name }}</h2>
        <span class="text-sm text-gray-400">{{ albumPhotos.length }} 张</span>
        <el-button v-if="currentAlbum && !currentAlbum.is_system" size="small" @click="openEditDialog(currentAlbum)" class="ml-auto">
          <el-icon><Edit /></el-icon> 编辑
        </el-button>
      </div>

      <!-- 详情加载 -->
      <div v-if="detailLoading" class="grid grid-cols-6 gap-3">
        <div v-for="i in 12" :key="i" class="aspect-square bg-gray-200 rounded-lg animate-pulse" />
      </div>

      <el-empty v-else-if="albumPhotos.length === 0" description="相册中还没有照片" />

      <div v-else class="grid grid-cols-6 gap-3">
        <div
          v-for="(photo, index) in albumPhotos"
          :key="photo.id"
          class="group relative aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer"
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
          <button
            class="absolute top-1 left-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
            @click.stop="handleRemovePhoto(photo)"
            title="从相册移除"
          >
            <el-icon :size="14"><Close /></el-icon>
          </button>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="detailTotal > detailPageSize" class="mt-4 flex justify-center">
        <el-pagination
          :current-page="detailPage"
          :page-size="detailPageSize"
          :total="detailTotal"
          @current-change="handleDetailPageChange"
        />
      </div>
    </template>

    <!-- 创建/编辑相册对话框 -->
    <el-dialog v-model="formDialogVisible" :title="editingAlbum ? '编辑相册' : '创建相册'" width="420px">
      <el-form :model="albumForm" label-width="70px">
        <el-form-item label="名称" required>
          <el-input v-model="albumForm.name" placeholder="输入相册名称" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="albumForm.description" type="textarea" :rows="3" placeholder="输入相册描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSubmitForm">
          {{ editingAlbum ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft, InfoFilled, Delete, Edit, Close, PictureFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { photoApi } from '@/api/photo'
import { albumApi } from '@/api/album'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { Album } from '@/types/album'
import type { PhotoItem } from '@/types/photo'

// ── 列表状态 ─────────────────
const loading = ref(true)
const albums = ref<Album[]>([])

// ── 视图切换（列表 / 详情） ─────────────────
const view = ref<'list' | 'detail'>('list')
const currentAlbum = ref<Album | null>(null)
const albumPhotos = ref<PhotoItem[]>([])
const detailLoading = ref(false)
const detailPage = ref(1)
const detailPageSize = 50
const detailTotal = ref(0)

async function openAlbum(album: Album) {
  currentAlbum.value = album
  view.value = 'detail'
  detailPage.value = 1
  await fetchAlbumPhotos()
}

function backToList() {
  view.value = 'list'
  currentAlbum.value = null
  albumPhotos.value = []
}

async function fetchAlbumPhotos() {
  if (!currentAlbum.value) return
  detailLoading.value = true
  try {
    const res = await albumApi.getPhotos(currentAlbum.value.id, {
      page: detailPage.value,
      page_size: detailPageSize,
    })
    albumPhotos.value = res.data.items
    detailTotal.value = res.data.total
  } catch {
    // handled by interceptor
  } finally {
    detailLoading.value = false
  }
}

function handleDetailPageChange(page: number) {
  detailPage.value = page
  fetchAlbumPhotos()
}

// ── 创建/编辑对话框 ─────────────────
const formDialogVisible = ref(false)
const formLoading = ref(false)
const editingAlbum = ref<Album | null>(null)
const albumForm = ref({ name: '', description: '' })

function openCreateDialog() {
  editingAlbum.value = null
  albumForm.value = { name: '', description: '' }
  formDialogVisible.value = true
}

function openEditDialog(album: Album) {
  editingAlbum.value = album
  albumForm.value = {
    name: album.name,
    description: album.description || '',
  }
  formDialogVisible.value = true
}

async function handleSubmitForm() {
  if (!albumForm.value.name.trim()) {
    ElMessage.warning('请输入相册名称')
    return
  }
  formLoading.value = true
  try {
    if (editingAlbum.value) {
      await albumApi.update(editingAlbum.value.id, {
        name: albumForm.value.name,
        description: albumForm.value.description || undefined,
      })
      ElMessage.success('相册更新成功')
    } else {
      await albumApi.create({
        name: albumForm.value.name,
        description: albumForm.value.description || undefined,
      })
      ElMessage.success('相册创建成功')
    }
    formDialogVisible.value = false
    await fetchAlbums()
    // 如果在详情页，且编辑的是当前相册，更新标题
    if (editingAlbum.value && currentAlbum.value?.id === editingAlbum.value.id) {
      currentAlbum.value = { ...currentAlbum.value, name: albumForm.value.name, description: albumForm.value.description || null }
    }
  } catch {
    // handled by interceptor
  } finally {
    formLoading.value = false
  }
}

// ── 删除相册 ─────────────────
async function confirmDeleteAlbum(album: Album) {
  try {
    await ElMessageBox.confirm(
      `确定要删除相册"${album.name}"吗？相册中的照片不会被删除。`,
      '删除相册',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await albumApi.delete(album.id)
    ElMessage.success('相册删除成功')
    await fetchAlbums()
  } catch {
    // 用户取消或接口错误（interceptor 处理）
  }
}

// ── 从相册移除照片 ─────────────────
async function handleRemovePhoto(photo: PhotoItem) {
  if (!currentAlbum.value) return
  try {
    await ElMessageBox.confirm(
      `确定要将"${photo.original_name || photo.filename}"从相册中移除吗？`,
      '移除照片',
      { confirmButtonText: '移除', cancelButtonText: '取消', type: 'warning' }
    )
    await albumApi.removePhoto(currentAlbum.value.id, photo.id)
    ElMessage.success('已从相册移除')
    await fetchAlbumPhotos()
    // 更新 photo_count
    currentAlbum.value = { ...currentAlbum.value, photo_count: currentAlbum.value.photo_count - 1 }
  } catch {
    // 用户取消
  }
}

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() =>
  albumPhotos.value.map((p) => photoApi.fileUrl(p.id))
)

function handlePreview(index: number) {
  previewIndex.value = index
  previewVisible.value = true
}

// ── 详情抽屉 ─────────────────
const detailVisible = ref(false)
const detailPhotoId = ref<string | null>(null)

function handleDetail(photo: PhotoItem) {
  detailPhotoId.value = photo.id
  detailVisible.value = true
}

// ── 加载相册列表 ─────────────────
async function fetchAlbums() {
  loading.value = true
  try {
    const res = await albumApi.list()
    albums.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(fetchAlbums)
</script>
