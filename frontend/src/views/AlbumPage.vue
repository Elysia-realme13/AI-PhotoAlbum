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
        <div class="ml-auto flex gap-2">
          <el-button type="primary" size="small" @click="openPhotoPicker">
            <el-icon><Plus /></el-icon> 添加照片
          </el-button>
          <el-button v-if="currentAlbum && !currentAlbum.is_system" size="small" @click="openEditDialog(currentAlbum)">
            <el-icon><Edit /></el-icon> 编辑
          </el-button>
        </div>
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
    <el-dialog v-model="formDialogVisible" :title="editingAlbum ? '编辑相册' : '创建相册'" width="480px">
      <el-form :model="albumForm" label-width="70px">
        <el-form-item label="名称" required>
          <el-input v-model="albumForm.name" placeholder="输入相册名称" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="albumForm.description" type="textarea" :rows="3" placeholder="输入相册描述（可选）" />
        </el-form-item>
        <!-- 相册类型（仅创建时可选） -->
        <template v-if="!editingAlbum">
          <el-form-item label="类型">
            <el-radio-group v-model="albumForm.album_type">
              <el-radio-button value="manual">手动相册</el-radio-button>
              <el-radio-button value="smart">智能相册</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <!-- 智能相册条件构造器 -->
          <template v-if="albumForm.album_type === 'smart'">
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="albumForm.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                class="!w-full"
              />
            </el-form-item>
            <el-form-item label="城市">
              <el-select
                v-model="albumForm.cities"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入城市名回车，可多个"
                class="w-full"
              />
            </el-form-item>
            <el-form-item label="标签">
              <el-select
                v-model="albumForm.tags"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入标签回车，可多个"
                class="w-full"
              />
            </el-form-item>
            <el-form-item label="人物">
              <el-select
                v-model="albumForm.identityIds"
                multiple
                filterable
                placeholder="选择人物"
                class="w-full"
              >
                <el-option
                  v-for="person in identityOptions"
                  :key="person.identity_id"
                  :label="person.identity_name || '未命名'"
                  :value="person.identity_id"
                />
              </el-select>
            </el-form-item>
            <p class="text-xs text-gray-400 pl-[70px] -mt-2">
              智能相册根据条件自动聚集照片，至少设置一项条件。
            </p>
          </template>
        </template>
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

    <!-- 添加照片对话框 -->
    <el-dialog v-model="photoPickerVisible" title="添加照片到相册" width="720px" top="5vh">
      <!-- 搜索栏 -->
      <div class="mb-4 flex gap-2">
        <el-input
          v-model="pickerSearch"
          placeholder="搜索照片..."
          clearable
          :prefix-icon="Search"
          @input="handlePickerSearch"
        />
      </div>

      <!-- 已选提示 -->
      <div v-if="selectedPhotoIds.size > 0" class="mb-3 text-sm text-blue-600">
        已选择 {{ selectedPhotoIds.size }} 张照片
      </div>

      <!-- 加载态 -->
      <div v-if="pickerLoading" class="grid grid-cols-6 gap-2 py-4">
        <div v-for="i in 12" :key="i" class="aspect-square bg-gray-200 rounded animate-pulse" />
      </div>

      <!-- 空状态 -->
      <el-empty v-else-if="pickerPhotos.length === 0" description="没有可添加的照片" :image-size="80" />

      <!-- 照片网格 -->
      <div v-else class="grid grid-cols-6 gap-2 max-h-[50vh] overflow-y-auto">
        <div
          v-for="photo in pickerPhotos"
          :key="photo.id"
          :class="[
            'relative aspect-square rounded-lg overflow-hidden cursor-pointer border-2 transition-all',
            selectedPhotoIds.has(photo.id)
              ? 'border-blue-500 ring-2 ring-blue-200'
              : 'border-transparent hover:border-gray-300'
          ]"
          @click="togglePhotoSelect(photo.id)"
        >
          <img :src="photoApi.thumbnailUrl(photo.id)" class="w-full h-full object-cover" />
          <!-- 选中标记 -->
          <div
            v-if="selectedPhotoIds.has(photo.id)"
            class="absolute top-1 right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center"
          >
            <el-icon :size="12" color="white"><Check /></el-icon>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="pickerTotal > pickerPageSize" class="mt-4 flex justify-center">
        <el-pagination
          v-model:current-page="pickerPage"
          :page-size="pickerPageSize"
          :total="pickerTotal"
          layout="prev, pager, next"
          @current-change="fetchPickerPhotos"
        />
      </div>

      <template #footer>
        <el-button @click="photoPickerVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="selectedPhotoIds.size === 0"
          :loading="addingPhotos"
          @click="handleAddPhotos"
        >
          添加 {{ selectedPhotoIds.size > 0 ? `(${selectedPhotoIds.size})` : '' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft, InfoFilled, Delete, Edit, Close, PictureFilled, Plus, Check, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { photoApi } from '@/api/photo'
import { albumApi } from '@/api/album'
import { faceApi } from '@/api/face'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { Album } from '@/types/album'
import type { PhotoItem } from '@/types/photo'
import type { FaceCluster } from '@/types/face'

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

interface AlbumFormState {
  name: string
  description: string
  album_type: 'manual' | 'smart'
  dateRange: [string, string] | null
  cities: string[]
  tags: string[]
  identityIds: string[]
}

function emptyForm(): AlbumFormState {
  return { name: '', description: '', album_type: 'manual', dateRange: null, cities: [], tags: [], identityIds: [] }
}

const albumForm = ref<AlbumFormState>(emptyForm())

// 智能相册人物选项
const identityOptions = ref<FaceCluster[]>([])
async function fetchIdentityOptions() {
  if (identityOptions.value.length > 0) return
  try {
    const res = await faceApi.listIdentities()
    identityOptions.value = res.data
  } catch {
    // handled by interceptor
  }
}

function openCreateDialog() {
  editingAlbum.value = null
  albumForm.value = emptyForm()
  formDialogVisible.value = true
  fetchIdentityOptions()
}

function openEditDialog(album: Album) {
  editingAlbum.value = album
  albumForm.value = {
    ...emptyForm(),
    name: album.name,
    description: album.description || '',
  }
  formDialogVisible.value = true
}

/** 根据表单组装智能相册条件 JSON */
function buildConditions(): Record<string, unknown> {
  const c: Record<string, unknown> = {}
  const f = albumForm.value
  if (f.dateRange && f.dateRange.length === 2) {
    c.date_from = f.dateRange[0]
    c.date_to = f.dateRange[1]
  }
  if (f.cities.length) c.cities = f.cities
  if (f.tags.length) c.tags = f.tags
  if (f.identityIds.length) c.identity_ids = f.identityIds
  return c
}

async function handleSubmitForm() {
  if (!albumForm.value.name.trim()) {
    ElMessage.warning('请输入相册名称')
    return
  }
  const isSmart = !editingAlbum.value && albumForm.value.album_type === 'smart'
  if (isSmart && Object.keys(buildConditions()).length === 0) {
    ElMessage.warning('智能相册至少需要设置一项条件')
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
    } else if (isSmart) {
      await albumApi.create({
        name: albumForm.value.name,
        description: albumForm.value.description || undefined,
        album_type: 'smart',
        conditions: buildConditions(),
      })
      ElMessage.success('智能相册创建成功')
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

// ── 照片选择器 ─────────────────
const photoPickerVisible = ref(false)
const pickerLoading = ref(false)
const pickerPhotos = ref<PhotoItem[]>([])
const pickerTotal = ref(0)
const pickerPage = ref(1)
const pickerPageSize = 48
const pickerSearch = ref('')
const selectedPhotoIds = ref<Set<string>>(new Set())
const addingPhotos = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | null = null

function openPhotoPicker() {
  photoPickerVisible.value = true
  pickerPage.value = 1
  pickerSearch.value = ''
  selectedPhotoIds.value = new Set()
  fetchPickerPhotos()
}

async function fetchPickerPhotos() {
  pickerLoading.value = true
  try {
    const res = await photoApi.list({
      page: pickerPage.value,
      page_size: pickerPageSize,
      sort_by: 'upload_time',
      order: 'desc',
    })
    const data = res.data.data || res.data
    pickerPhotos.value = data.items || []
    pickerTotal.value = data.total || 0
  } catch {
    // handled by interceptor
  } finally {
    pickerLoading.value = false
  }
}

function handlePickerSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pickerPage.value = 1
    fetchPickerPhotos()
  }, 300)
}

function togglePhotoSelect(id: string) {
  const newSet = new Set(selectedPhotoIds.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedPhotoIds.value = newSet
}

async function handleAddPhotos() {
  if (!currentAlbum.value || selectedPhotoIds.value.size === 0) return
  addingPhotos.value = true
  try {
    const ids = Array.from(selectedPhotoIds.value)
    // 并行添加所有照片
    await Promise.all(ids.map(id => albumApi.addPhoto(currentAlbum.value!.id, id)))
    ElMessage.success(`已添加 ${ids.length} 张照片到相册`)
    photoPickerVisible.value = false
    selectedPhotoIds.value = new Set()
    // 刷新相册照片列表
    await fetchAlbumPhotos()
    // 更新相册照片计数
    if (currentAlbum.value) {
      currentAlbum.value = {
        ...currentAlbum.value,
        photo_count: currentAlbum.value.photo_count + ids.length,
      }
    }
  } catch {
    // handled by interceptor
  } finally {
    addingPhotos.value = false
  }
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
