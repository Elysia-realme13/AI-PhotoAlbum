<template>
  <div>
    <!-- 相册列表视图 -->
    <template v-if="view === 'list'">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800">相册</h2>
        <el-button type="primary" @click="showCreateDialog = true">
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
        <el-empty v-if="albums.length === 0" description="还没有照片，快去上传吧！" />
        <div v-else class="grid grid-cols-4 gap-4">
          <div
            v-for="album in albums"
            :key="album.key"
            class="group bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100 cursor-pointer hover:shadow-md transition-shadow relative"
            @click="openAlbum(album)"
          >
            <div class="relative aspect-square bg-gray-100 overflow-hidden">
              <img
                :src="photoApi.thumbnailUrl(album.photos[0].id)"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform"
              />
              <span class="absolute bottom-2 right-2 px-2 py-0.5 rounded-full bg-black/50 text-white text-xs">
                {{ album.photos.length }} 张
              </span>
            </div>
            <div class="p-3">
              <p class="text-sm font-medium text-gray-800 truncate">{{ album.title }}</p>
              <p class="text-xs text-gray-400 mt-0.5">{{ album.photos.length }} 张照片</p>
            </div>
            <!-- 删除按钮 -->
            <button
              class="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
              @click.stop="confirmDeleteAlbum(album)"
              title="删除相册"
            >
              <el-icon :size="16"><Delete /></el-icon>
            </button>
          </div>
        </div>
      </template>
    </template>

    <!-- 相册详情视图 -->
    <template v-else>
      <div class="flex items-center gap-3 mb-6">
        <el-button :icon="ArrowLeft" circle @click="backToList" aria-label="返回相册列表" />
        <h2 class="text-2xl font-bold text-gray-800">{{ currentAlbum?.title }}</h2>
        <span class="text-sm text-gray-400">{{ currentAlbum?.photos.length }} 张</span>
      </div>

      <div class="grid grid-cols-6 gap-3">
        <div
          v-for="(photo, index) in currentAlbum?.photos"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft, InfoFilled, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { photoApi } from '@/api/photo'
import { loadAllPhotos } from '@/api/search'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'

interface TimeAlbum {
  key: string
  title: string
  photos: PhotoItem[]
}

const loading = ref(true)
const albums = ref<TimeAlbum[]>([])
const showCreateDialog = ref(false)

// ── 视图切换（列表 / 详情） ─────────────────
const view = ref<'list' | 'detail'>('list')
const currentAlbum = ref<TimeAlbum | null>(null)

function openAlbum(album: TimeAlbum) {
  currentAlbum.value = album
  view.value = 'detail'
}

function backToList() {
  view.value = 'list'
  currentAlbum.value = null
}

// ── 删除相册 ─────────────────
async function confirmDeleteAlbum(album: TimeAlbum) {
  try {
    await ElMessageBox.confirm(
      `确定要删除相册"${album.title}"吗？相册中的照片不会被删除。`,
      '删除相册',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 从列表中移除
    albums.value = albums.value.filter(a => a.key !== album.key)
    ElMessage.success('相册删除成功')
  } catch {
    // 用户取消
  }
}

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() =>
  (currentAlbum.value?.photos || []).map((p) => photoApi.fileUrl(p.id))
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

// ── 按拍摄时间分组为虚拟相册 ─────────────────
const UNKNOWN_KEY = 'unknown'

function photoTimestamp(p: PhotoItem): string | undefined {
  return p.photo_time || p.upload_time
}

function groupByMonth(photos: PhotoItem[]): TimeAlbum[] {
  const map = new Map<string, PhotoItem[]>()

  for (const photo of photos) {
    const ts = photoTimestamp(photo)
    let key = UNKNOWN_KEY
    if (ts) {
      const d = new Date(ts)
      if (!isNaN(d.getTime())) {
        key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      }
    }
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(photo)
  }

  const result: TimeAlbum[] = []
  for (const [key, items] of map.entries()) {
    // 组内按时间倒序
    items.sort((a, b) => (photoTimestamp(b) || '') > (photoTimestamp(a) || '') ? 1 : -1)
    const title =
      key === UNKNOWN_KEY
        ? '未知时间'
        : `${key.slice(0, 4)}年${key.slice(5, 7)}月`
    result.push({ key, title, photos: items })
  }

  // 组间按月份倒序，未知时间排最后
  result.sort((a, b) => {
    if (a.key === UNKNOWN_KEY) return 1
    if (b.key === UNKNOWN_KEY) return -1
    return b.key > a.key ? 1 : -1
  })

  return result
}

async function fetchData() {
  loading.value = true
  try {
    const photos = await loadAllPhotos()
    albums.value = groupByMonth(photos)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
