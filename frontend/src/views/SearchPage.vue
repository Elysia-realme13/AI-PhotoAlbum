<template>
  <div class="search-page">
    <!-- 顶部标题 -->
    <div class="page-header">
      <h1>智能搜索</h1>
      <p class="text-gray-500 dark:text-dark-text-secondary">在你的相册中快速查找照片</p>
    </div>

    <!-- 搜索栏 -->
    <div class="search-box">
      <div class="search-controls">
        <el-input
          v-model="searchQuery"
          placeholder="输入照片名称或关键词..."
          clearable
          @keyup.enter="handleSearch"
          class="search-input"
        />
        <div class="mode-buttons">
          <el-radio-group v-model="searchMode" class="ml-4">
            <el-radio-button label="semantic">语义搜索</el-radio-button>
            <el-radio-button label="keyword">关键词</el-radio-button>
            <el-radio-button label="tag">标签</el-radio-button>
          </el-radio-group>
        </div>
        <el-button type="primary" @click="handleSearch" class="ml-4">搜索</el-button>
      </div>

      <!-- 日期筛选 -->
      <div class="mt-4">
        <label class="block text-sm font-medium mb-2">日期范围</label>
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleFilterChange"
          style="max-width: 360px"
        />
      </div>
    </div>

    <!-- 结果统计和推荐标签 -->
    <div v-if="searchResults.items && searchResults.items.length > 0" class="results-header mt-6">
      <div class="flex justify-between items-start">
        <p class="text-lg font-medium dark:text-dark-text">
          找到 <span class="text-blue-600 font-bold">{{ searchResults.total }}</span> 张相关照片
        </p>
        <div v-if="searchResults.suggested_tags.length > 0" class="suggested-tags">
          <span class="text-sm text-gray-600 dark:text-dark-text-secondary mr-2">推荐标签:</span>
          <el-tag
            v-for="tag in searchResults.suggested_tags.slice(0, 5)"
            :key="tag"
            clickable
            @click="selectSuggestedTag(tag)"
            class="mr-2 cursor-pointer"
          >
            {{ tag }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 结果区 -->
    <div class="results-container mt-6">
      <!-- 未搜索状态 -->
      <div v-if="!hasSearched" class="empty-state">
        <el-empty description="开始搜索你的照片">
          <template #default>
            <div v-if="exampleQueries.length > 0" class="mt-4">
              <span class="text-sm text-gray-600 dark:text-dark-text-secondary mr-2">示例搜索:</span>
              <el-tag
                v-for="example in exampleQueries"
                :key="example"
                clickable
                @click="selectExampleQuery(example)"
                class="mr-2 cursor-pointer"
              >
                {{ example }}
              </el-tag>
            </div>
          </template>
        </el-empty>
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" class="skeleton-grid">
        <div v-for="i in 12" :key="i" class="skeleton-item">
          <div class="skeleton-image"></div>
          <div class="skeleton-text"></div>
        </div>
      </div>

      <!-- 无结果 -->
      <div v-else-if="searchResults.items.length === 0" class="empty-state">
        <el-empty description="未找到相关照片">
          <template #default>
            <p class="text-sm text-gray-500 dark:text-dark-text-secondary mb-3">试试换个关键词，或调整筛选条件</p>
            <el-button type="primary" size="small" @click="resetSearch">重置搜索</el-button>
          </template>
        </el-empty>
      </div>

      <!-- 有结果网格 -->
      <div v-else class="photo-grid">
        <div
          v-for="photo in searchResults.items"
          :key="photo.id"
          class="photo-card group"
          @click="previewPhoto(photo)"
        >
          <div class="photo-container">
            <el-image
              :src="photo.thumbnail_url"
              fit="cover"
              loading="lazy"
              class="photo-image"
            />
            <!-- 相似度角标 -->
            <div
              v-if="searchResults.mode === 'semantic' && photo.score !== undefined"
              class="score-badge"
            >
              {{ (photo.score * 100).toFixed(0) }}%
            </div>
            <!-- 详情按钮 -->
            <button
              class="absolute top-1 right-1 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500"
              @click.stop="handleDetail(photo)"
              title="详情"
            >
              <el-icon :size="14"><InfoFilled /></el-icon>
            </button>
          </div>
          <div class="photo-info">
            <p class="photo-name truncate text-sm font-medium">
              {{ photo.original_name || '未命名' }}
            </p>
            <p v-if="photo.city" class="photo-city text-xs text-gray-500 dark:text-dark-text-secondary">
              {{ photo.city }}
            </p>
            <p v-if="photo.photo_time" class="photo-time text-xs text-gray-500 dark:text-dark-text-secondary">
              {{ formatDate(photo.photo_time) }}
            </p>
            <div v-if="photo.tags.length > 0" class="photo-tags mt-1">
              <el-tag
                v-for="tag in photo.tags.slice(0, 2)"
                :key="tag"
                type="info"
                size="small"
                class="mr-1"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="searchResults.total > pageSize" class="pagination mt-6 flex justify-center">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :total="searchResults.total"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewUrls"
      :initial-index="previewIndex"
      @close="previewVisible = false"
    />

    <!-- 详情抽屉 -->
    <PhotoDetailDrawer v-model:visible="detailVisible" :photo-id="detailPhotoId" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { loadAllPhotos, searchPhotos } from '@/api/search'
import { photoApi } from '@/api/photo'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'
import type { SearchRequest, SearchResponse, SearchResultItem } from '@/types/search'

// 搜索状态
const searchQuery = ref('')
const searchMode = ref<'semantic' | 'keyword' | 'tag'>('semantic')
const loading = ref(false)
const hasSearched = ref(false)

// 筛选条件（仅日期范围）
const filters = reactive({
  dateRange: null as [Date, Date] | null,
})

// 搜索结果
const searchResults = reactive<SearchResponse>({
  items: [],
  total: 0,
  query: '',
  mode: 'semantic',
  suggested_tags: [],
})

// 分页
const currentPage = ref(1)
const pageSize = 40

// 预览
const previewVisible = ref(false)
const previewIndex = ref(0)
const previewUrls = ref<string[]>([])

// 所有照片缓存
let allPhotos: PhotoItem[] = []

// 示例查询（从真实文件名提取）
const exampleQueries = ref<string[]>([])

// 详情抽屉
const detailVisible = ref(false)
const detailPhotoId = ref<string | null>(null)

/**
 * 格式化日期
 */
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN')
  } catch {
    return dateStr
  }
}

/**
 * 处理搜索
 */
async function handleSearch() {
  try {
    loading.value = true
    currentPage.value = 1

    const request: SearchRequest = {
      query: searchQuery.value,
      mode: searchMode.value,
      filters: {
        start_date: filters.dateRange?.[0]
          ? filters.dateRange[0].toISOString().split('T')[0]
          : undefined,
        end_date: filters.dateRange?.[1]
          ? filters.dateRange[1].toISOString().split('T')[0]
          : undefined,
      },
      page: currentPage.value,
      page_size: pageSize,
    }

    const result = searchPhotos(request, allPhotos)
    Object.assign(searchResults, result)
    hasSearched.value = true
  } catch (error) {
    console.error('搜索出错:', error)
    ElMessage.error('搜索失败，请重试')
  } finally {
    loading.value = false
  }
}

/**
 * 处理筛选条件变化
 */
function handleFilterChange() {
  if (hasSearched.value) {
    handleSearch()
  }
}

/**
 * 处理分页
 */
function handlePageChange(page: number) {
  currentPage.value = page
  handleSearch()
}

/**
 * 选择推荐标签
 */
function selectSuggestedTag(tag: string) {
  searchMode.value = 'tag'
  searchQuery.value = tag
  filters.dateRange = null
  handleSearch()
}

/**
 * 选择示例查询
 */
function selectExampleQuery(query: string) {
  searchQuery.value = query
  searchMode.value = 'semantic'
  filters.dateRange = null
  handleSearch()
}

/**
 * 重置搜索（回到未搜索态）
 */
function resetSearch() {
  searchQuery.value = ''
  searchMode.value = 'semantic'
  filters.dateRange = null
  searchResults.items = []
  searchResults.total = 0
  searchResults.query = ''
  searchResults.suggested_tags = []
  hasSearched.value = false
  currentPage.value = 1
}

/**
 * 打开详情抽屉
 */
function handleDetail(photo: SearchResultItem) {
  detailPhotoId.value = photo.id
  detailVisible.value = true
}

/**
 * 预览照片
 */
function previewPhoto(photo: SearchResultItem) {
  previewIndex.value = searchResults.items.indexOf(photo)
  previewUrls.value = searchResults.items.map((p) => photoApi.fileUrl(p.id))
  previewVisible.value = true
}

/**
 * 初始化：加载照片
 */
onMounted(async () => {
  try {
    loading.value = true
    allPhotos = await loadAllPhotos()

    // 从真实文件名中提取示例查询（去重、长度适中）
    const seen = new Set<string>()
    const examples: string[] = []
    for (const photo of allPhotos) {
      if (!photo.original_name) continue
      const name = photo.original_name
      if (name.length < 3 || name.length > 30) continue
      if (seen.has(name)) continue
      seen.add(name)
      examples.push(name)
      if (examples.length >= 4) break
    }
    exampleQueries.value = examples
  } catch (error) {
    console.error('加载照片失败:', error)
    // 区分不同错误类型
    const axiosError = error as any
    if (axiosError?.response?.status === 400) {
      ElMessage.error('请求参数错误，请刷新重试')
    } else if (axiosError?.response?.status === 401) {
      ElMessage.error('认证失败，请重新登录')
    } else {
      ElMessage.error('加载照片失败，请刷新重试')
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.search-page {
  @apply p-6 max-w-7xl mx-auto;
}

.page-header {
  @apply mb-6;

  h1 {
    @apply text-3xl font-bold text-gray-900;
  }

  p {
    @apply mt-1;
  }
}

.search-box {
  @apply bg-white dark:bg-dark-card rounded-lg shadow p-6;
}

.search-controls {
  @apply flex flex-wrap gap-4 items-center;

  .search-input {
    @apply flex-1;
  }

  .mode-buttons {
    @apply flex-shrink-0;
  }
}

.results-header {
  @apply bg-white dark:bg-dark-card rounded-lg shadow p-4;
}

.suggested-tags {
  @apply flex items-center flex-wrap gap-2;
}

.results-container {
  @apply bg-white dark:bg-dark-card rounded-lg shadow p-6;
}

.empty-state {
  @apply py-12 flex justify-center;
}

.skeleton-grid {
  @apply grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4;
}

.skeleton-item {
  @apply space-y-2;

  .skeleton-image {
    @apply w-full aspect-square bg-gray-200 dark:bg-dark-hover rounded animate-pulse;
  }

  .skeleton-text {
    @apply h-4 bg-gray-200 dark:bg-dark-hover rounded animate-pulse;
  }
}

.photo-grid {
  @apply grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4;
}

.photo-card {
  @apply bg-white dark:bg-dark-card rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer;

  .photo-container {
    @apply relative overflow-hidden bg-gray-100 dark:bg-dark-hover aspect-square;

    .photo-image {
      @apply w-full h-full object-cover hover:scale-105 transition-transform;
    }

    .score-badge {
      @apply absolute top-2 right-2 bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded;
    }
  }

  .photo-info {
    @apply p-3 space-y-1;

    .photo-name {
      @apply text-gray-900 dark:text-dark-text;
    }

    .photo-city,
    .photo-time {
      @apply text-gray-500 dark:text-dark-text-secondary;
    }

    .photo-tags {
      @apply flex flex-wrap gap-1;
    }
  }
}

.pagination {
  @apply bg-white dark:bg-dark-card rounded-lg shadow p-4;
}
</style>
