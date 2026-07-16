<template>
  <div>
    <!-- 人物列表视图 -->
    <template v-if="view === 'list'">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">人物</h2>
        <p class="text-sm text-gray-400 dark:text-dark-text-secondary">系统自动识别照片中的人脸并聚类</p>
      </div>

      <!-- 加载骨架屏 -->
      <div v-if="loading" class="grid grid-cols-4 gap-4">
        <div v-for="i in 8" :key="i" class="bg-white dark:bg-dark-card rounded-xl p-4 shadow-sm border border-gray-100 dark:border-dark-border flex flex-col items-center">
          <div class="w-20 h-20 rounded-full bg-gray-200 dark:bg-dark-hover animate-pulse mb-3" />
          <div class="h-4 bg-gray-200 dark:bg-dark-hover rounded w-16 mb-2 animate-pulse" />
          <div class="h-3 bg-gray-200 dark:bg-dark-hover rounded w-10 animate-pulse" />
        </div>
      </div>

      <template v-else>
        <el-empty v-if="identities.length === 0" description="还没有识别到人物，上传照片后系统会自动识别" />
        <div v-else class="grid grid-cols-4 gap-4">
          <div
            v-for="person in identities"
            :key="person.identity_id"
            class="group relative bg-white dark:bg-dark-card rounded-xl p-4 shadow-sm border border-gray-100 dark:border-dark-border cursor-pointer hover:shadow-md transition-shadow flex flex-col items-center"
            @click="openPerson(person)"
          >
            <!-- 圆形头像 -->
            <div class="w-20 h-20 rounded-full overflow-hidden bg-blue-500 text-white flex items-center justify-center text-2xl font-bold mb-3">
              <img
                v-if="person.cover_photo_id"
                :src="photoApi.thumbnailUrl(person.cover_photo_id)"
                class="w-full h-full object-cover"
              />
              <span v-else>{{ personInitial(person) }}</span>
            </div>
            <p class="text-sm font-medium text-gray-800 dark:text-dark-text truncate max-w-full">
              {{ person.identity_name || '未命名' }}
            </p>
            <p class="text-xs text-gray-400 dark:text-dark-text-secondary mt-0.5">{{ person.face_count }} 张照片</p>

            <!-- hover 重命名按钮 -->
            <button
              class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500"
              @click.stop="renamePerson(person)"
              title="重命名"
            >
              <el-icon :size="14"><EditPen /></el-icon>
            </button>
          </div>
        </div>
      </template>
    </template>

    <!-- 人物详情视图 -->
    <template v-else>
      <div class="flex items-center gap-3 mb-6">
        <el-button :icon="ArrowLeft" circle @click="backToList" aria-label="返回人物列表" />
        <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">{{ currentPerson?.identity_name || '未命名' }}</h2>
        <button
          class="w-7 h-7 rounded-full hover:bg-gray-100 dark:hover:bg-dark-hover flex items-center justify-center text-gray-400 hover:text-blue-500 dark:text-dark-text-secondary"
          @click="currentPerson && renamePerson(currentPerson)"
          title="重命名"
        >
          <el-icon :size="16"><EditPen /></el-icon>
        </button>
        <span class="text-sm text-gray-400 dark:text-dark-text-secondary">{{ currentPhotos.length }} 张</span>
      </div>

      <div v-if="detailLoading" class="grid grid-cols-6 gap-3">
        <div v-for="i in 12" :key="i" class="aspect-square bg-gray-200 dark:bg-dark-hover rounded-lg animate-pulse" />
      </div>
      <div v-else class="grid grid-cols-6 gap-3">
        <div
          v-for="(photo, index) in currentPhotos"
          :key="photo.id"
          class="group relative aspect-square bg-gray-100 dark:bg-dark-hover rounded-lg overflow-hidden cursor-pointer"
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, InfoFilled, EditPen } from '@element-plus/icons-vue'
import { photoApi } from '@/api/photo'
import { faceApi } from '@/api/face'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'
import type { FaceCluster } from '@/types/face'

// ── 状态 ─────────────────────────
const loading = ref(true)
const identities = ref<FaceCluster[]>([])

const view = ref<'list' | 'detail'>('list')
const currentPerson = ref<FaceCluster | null>(null)
const currentPhotos = ref<PhotoItem[]>([])
const detailLoading = ref(false)

// ── 工具 ─────────────────────────
function personInitial(person: FaceCluster): string {
  const name = person.identity_name || '?'
  return name.charAt(0).toUpperCase()
}

// ── 列表数据 ─────────────────────────
async function fetchIdentities() {
  loading.value = true
  try {
    const res = await faceApi.listIdentities()
    identities.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

// ── 详情：加载某人物的照片 ─────────────────
async function openPerson(person: FaceCluster) {
  currentPerson.value = person
  view.value = 'detail'
  detailLoading.value = true
  try {
    const res = await faceApi.identityPhotos(person.identity_id)
    currentPhotos.value = res.data
  } catch {
    // handled by interceptor
  } finally {
    detailLoading.value = false
  }
}

function backToList() {
  view.value = 'list'
  currentPerson.value = null
  currentPhotos.value = []
}

// ── 重命名 ─────────────────────────
async function renamePerson(person: FaceCluster) {
  try {
    const { value } = await ElMessageBox.prompt('请输入人物名称', '重命名', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: person.identity_name || '',
      inputValidator: (v: string) => (v && v.trim().length > 0 ? true : '名称不能为空'),
    })
    const newName = value.trim()
    await faceApi.renameCluster(person.identity_id, newName)
    // 同步更新本地状态
    person.identity_name = newName
    const target = identities.value.find((p) => p.identity_id === person.identity_id)
    if (target) target.identity_name = newName
    if (currentPerson.value?.identity_id === person.identity_id) currentPerson.value.identity_name = newName
    ElMessage.success('已重命名')
  } catch {
    // 用户取消或请求失败
  }
}

// ── 图片预览 ─────────────────────────
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewList = computed(() => currentPhotos.value.map((p) => photoApi.fileUrl(p.id)))

function handlePreview(index: number) {
  previewIndex.value = index
  previewVisible.value = true
}

// ── 详情抽屉 ─────────────────────────
const detailVisible = ref(false)
const detailPhotoId = ref<string | null>(null)

function handleDetail(photo: PhotoItem) {
  detailPhotoId.value = photo.id
  detailVisible.value = true
}

// ── 初始化 ─────────────────────────
onMounted(fetchIdentities)
</script>
