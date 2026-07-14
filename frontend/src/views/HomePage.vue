<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 mb-6">首页</h2>

    <!-- 加载骨架屏 -->
    <div v-if="loading">
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div v-for="i in 4" :key="i" class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="h-3 bg-gray-200 rounded w-16 mb-3 animate-pulse" />
              <div class="h-8 bg-gray-200 rounded w-12 animate-pulse" />
            </div>
            <div class="w-12 h-12 rounded-lg bg-gray-200 animate-pulse" />
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div class="h-5 bg-gray-200 rounded w-24 mb-4 animate-pulse" />
        <div class="grid grid-cols-6 gap-3">
          <div v-for="i in 6" :key="i" class="aspect-square bg-gray-200 rounded-lg animate-pulse" />
        </div>
      </div>
    </div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 text-sm">总照片数</p>
              <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.photos }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center">
              <el-icon :size="24" color="#409EFF"><PictureFilled /></el-icon>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 text-sm">相册数</p>
              <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.albums }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-green-50 flex items-center justify-center">
              <el-icon :size="24" color="#67C23A"><Folder /></el-icon>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 text-sm">识别人物</p>
              <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.faces }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-purple-50 flex items-center justify-center">
              <el-icon :size="24" color="#9C27B0"><UserFilled /></el-icon>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 text-sm">足迹城市</p>
              <p class="text-3xl font-bold text-gray-800 mt-1">{{ stats.cities }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-orange-50 flex items-center justify-center">
              <el-icon :size="24" color="#E6A23C"><Location /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近上传 -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h3 class="text-lg font-semibold text-gray-800 mb-4">最近上传</h3>
        <el-empty v-if="recentPhotos.length === 0" description="还没有照片，快去上传吧！" />
        <div v-else class="grid grid-cols-6 gap-3">
          <div
            v-for="(photo, index) in recentPhotos"
            :key="photo.id"
            class="group relative aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer"
            @click="handlePreview(photo, index)"
          >
            <img :src="photoApi.thumbnailUrl(photo.id)" class="w-full h-full object-cover group-hover:opacity-80 transition-opacity" />
            <button
              class="absolute top-1 right-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500"
              @click.stop="handleDetail(photo)"
              title="详情"
            >
              <el-icon :size="14"><InfoFilled /></el-icon>
            </button>
          </div>
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
import { InfoFilled } from '@element-plus/icons-vue'
import { photoApi } from '@/api/photo'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'

const loading = ref(true)

const stats = ref({
  photos: 0,
  albums: 0,
  faces: 0,
  cities: 0,
})

const recentPhotos = ref<PhotoItem[]>([])

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() =>
  recentPhotos.value.map((p) => photoApi.fileUrl(p.id))
)

function handlePreview(_photo: PhotoItem, index: number) {
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

// ── 加载数据 ─────────────────────────
async function fetchData() {
  loading.value = true
  try {
    const [statsRes, recentRes] = await Promise.all([
      photoApi.list({ page: 1, page_size: 1 }),
      photoApi.list({ page: 1, page_size: 6, sort_by: 'upload_time', sort_order: 'desc' }),
    ])
    stats.value.photos = statsRes.data.total
    recentPhotos.value = recentRes.data.items
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
