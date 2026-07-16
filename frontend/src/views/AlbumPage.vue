<template>
  <div>
    <!-- 鐩稿唽鍒楄〃瑙嗗浘 -->
    <template v-if="view === 'list'">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800">鐩稿唽</h2>
        <el-button type="primary" @click="openCreateDialog">
          鍒涘缓鐩稿唽
        </el-button>
      </div>

      <!-- 鍔犺浇楠ㄦ灦灞?-->
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
        <el-empty v-if="albums.length === 0" description="杩樻病鏈夌浉鍐岋紝鐐瑰嚮銆愬垱寤虹浉鍐屻€戝紑濮嬫暣鐞嗙収鐗囧惂锛? />
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
                {{ album.photo_count }} 寮?              </span>
            </div>
            <div class="p-3">
              <p class="text-sm font-medium text-gray-800 truncate">{{ album.name }}</p>
              <p class="text-xs text-gray-400 mt-0.5">
                {{ album.description || '鏃犳弿杩? }}
              </p>
            </div>
            <!-- 鎿嶄綔鎸夐挳 -->
            <div class="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                class="w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-blue-500"
                @click.stop="openEditDialog(album)"
                title="缂栬緫"
              >
                <el-icon :size="14"><Edit /></el-icon>
              </button>
              <button
                v-if="!album.is_system"
                class="w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-red-500"
                @click.stop="confirmDeleteAlbum(album)"
                title="鍒犻櫎鐩稿唽"
              >
                <el-icon :size="16"><Delete /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- 鐩稿唽璇︽儏瑙嗗浘 -->
    <template v-else>
      <div class="flex items-center gap-3 mb-6">
        <el-button :icon="ArrowLeft" circle @click="backToList" aria-label="杩斿洖鐩稿唽鍒楄〃" />
        <h2 class="text-2xl font-bold text-gray-800">{{ currentAlbum?.name }}</h2>
        <span class="text-sm text-gray-400">{{ albumPhotos.length }} 寮?/span>
        <el-button v-if="currentAlbum && !currentAlbum.is_system" size="small" @click="openEditDialog(currentAlbum)" class="ml-auto">
          <el-icon><Edit /></el-icon> 缂栬緫
        </el-button>
      </div>

      <!-- 璇︽儏鍔犺浇 -->
      <div v-if="detailLoading" class="grid grid-cols-6 gap-3">
        <div v-for="i in 12" :key="i" class="aspect-square bg-gray-200 rounded-lg animate-pulse" />
      </div>

      <el-empty v-else-if="albumPhotos.length === 0" description="鐩稿唽涓繕娌℃湁鐓х墖" />

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
            title="璇︽儏"
          >
            <el-icon :size="14"><InfoFilled /></el-icon>
          </button>
          <button
            class="absolute top-1 left-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
            @click.stop="handleRemovePhoto(photo)"
            title="浠庣浉鍐岀Щ闄?
          >
            <el-icon :size="14"><Close /></el-icon>
          </button>
        </div>
      </div>

      <!-- 鍒嗛〉 -->
      <div v-if="detailTotal > detailPageSize" class="mt-4 flex justify-center">
        <el-pagination
          :current-page="detailPage"
          :page-size="detailPageSize"
          :total="detailTotal"
          @current-change="handleDetailPageChange"
        />
      </div>
    </template>

    <!-- 鍒涘缓/缂栬緫鐩稿唽瀵硅瘽妗?-->
    <el-dialog v-model="formDialogVisible" :title="editingAlbum ? '缂栬緫鐩稿唽' : '鍒涘缓鐩稿唽'" width="420px">
      <el-form :model="albumForm" label-width="70px">
        <el-form-item label="鍚嶇О" required>
          <el-input v-model="albumForm.name" placeholder="杈撳叆鐩稿唽鍚嶇О" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="鎻忚堪">
          <el-input v-model="albumForm.description" type="textarea" :rows="3" placeholder="杈撳叆鐩稿唽鎻忚堪锛堝彲閫夛級" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">鍙栨秷</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSubmitForm">
          {{ editingAlbum ? '淇濆瓨' : '鍒涘缓' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 鍥剧墖棰勮 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewList"
      :initial-index="previewIndex"
      @close="previewVisible = false"
      :hide-on-click-modal="true"
    />

    <!-- 璇︽儏鎶藉眽 -->
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

// 鈹€鈹€ 鍒楄〃鐘舵€?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
const loading = ref(true)
const albums = ref<Album[]>([])

// 鈹€鈹€ 瑙嗗浘鍒囨崲锛堝垪琛?/ 璇︽儏锛?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
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

// 鈹€鈹€ 鍒涘缓/缂栬緫瀵硅瘽妗?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
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
    ElMessage.warning('璇疯緭鍏ョ浉鍐屽悕绉?)
    return
  }
  formLoading.value = true
  try {
    if (editingAlbum.value) {
      await albumApi.update(editingAlbum.value.id, {
        name: albumForm.value.name,
        description: albumForm.value.description || undefined,
      })
      ElMessage.success('鐩稿唽鏇存柊鎴愬姛')
    } else {
      await albumApi.create({
        name: albumForm.value.name,
        description: albumForm.value.description || undefined,
      })
      ElMessage.success('鐩稿唽鍒涘缓鎴愬姛')
    }
    formDialogVisible.value = false
    await fetchAlbums()
    // 濡傛灉鍦ㄨ鎯呴〉锛屼笖缂栬緫鐨勬槸褰撳墠鐩稿唽锛屾洿鏂版爣棰?    if (editingAlbum.value && currentAlbum.value?.id === editingAlbum.value.id) {
      currentAlbum.value = { ...currentAlbum.value, name: albumForm.value.name, description: albumForm.value.description || null }
    }
  } catch {
    // handled by interceptor
  } finally {
    formLoading.value = false
  }
}

// 鈹€鈹€ 鍒犻櫎鐩稿唽 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
async function confirmDeleteAlbum(album: Album) {
  try {
    await ElMessageBox.confirm(
      `纭畾瑕佸垹闄ょ浉鍐?${album.name}"鍚楋紵鐩稿唽涓殑鐓х墖涓嶄細琚垹闄ゃ€俙,
      '鍒犻櫎鐩稿唽',
      {
        confirmButtonText: '鍒犻櫎',
        cancelButtonText: '鍙栨秷',
        type: 'warning',
      }
    )
    await albumApi.delete(album.id)
    ElMessage.success('鐩稿唽鍒犻櫎鎴愬姛')
    await fetchAlbums()
  } catch {
    // 鐢ㄦ埛鍙栨秷鎴栨帴鍙ｉ敊璇紙interceptor 澶勭悊锛?  }
}

// 鈹€鈹€ 浠庣浉鍐岀Щ闄ょ収鐗?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
async function handleRemovePhoto(photo: PhotoItem) {
  if (!currentAlbum.value) return
  try {
    await ElMessageBox.confirm(
      `纭畾瑕佸皢"${photo.original_name || photo.filename}"浠庣浉鍐屼腑绉婚櫎鍚楋紵`,
      '绉婚櫎鐓х墖',
      { confirmButtonText: '绉婚櫎', cancelButtonText: '鍙栨秷', type: 'warning' }
    )
    await albumApi.removePhoto(currentAlbum.value.id, photo.id)
    ElMessage.success('宸蹭粠鐩稿唽绉婚櫎')
    await fetchAlbumPhotos()
    // 鏇存柊 photo_count
    currentAlbum.value = { ...currentAlbum.value, photo_count: currentAlbum.value.photo_count - 1 }
  } catch {
    // 鐢ㄦ埛鍙栨秷
  }
}

// 鈹€鈹€ 鍥剧墖棰勮 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() =>
  albumPhotos.value.map((p) => photoApi.fileUrl(p.id))
)

function handlePreview(index: number) {
  previewIndex.value = index
  previewVisible.value = true
}

// 鈹€鈹€ 璇︽儏鎶藉眽 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
const detailVisible = ref(false)
const detailPhotoId = ref<string | null>(null)

function handleDetail(photo: PhotoItem) {
  detailPhotoId.value = photo.id
  detailVisible.value = true
}

// 鈹€鈹€ 鍔犺浇鐩稿唽鍒楄〃 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
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
