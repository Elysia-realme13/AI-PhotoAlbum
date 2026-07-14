<template>
  <div class="search-page">
    <!-- 顶部标题 -->
    <div class="page-header">
      <h1>智能搜索</h1>
      <p class="text-gray-500">在你的相册中快速查找照片</p>
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

      <!-- 展开/收起筛选 -->
      <div class="filter-toggle mt-3">
        <el-button link type="primary" @click="showFilters = !showFilters">
          {{ showFilters ? '收起筛选' : '展开筛选' }}
        </el-button>
      </div>

      <!-- 筛选区 -->
      <el-collapse-transition>
        <div v-show="showFilters" class="filters-panel mt-4 p-4 bg-gray-50 rounded">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 日期范围 -->
            <div>
              <label class="block text-sm font-medium mb-2">日期范围</label>
              <el-date-picker
                v-model="filters.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                @change="handleFilterChange"
                class="w-full"
              />
            </div>

            <!-- 城市 -->
            <div>
              <label class="block text-sm font-medium mb-2">城市</label>
              <el-select
                v-model="filters.city"
                placeholder="选择城市"
                clearable
                @change="handleFilterChange"
                class="w-full"
              >
                <el-option
                  v-for="city in availableCities"
                  :key="city"
                  :label="city"
                  :value="city"
                />
              </el-select>
            </div>

            <!-- 标签 -->
            <div>
              <label class="block text-sm font-medium mb-2">标签</label>
              <el-select
                v-model="filters.tags"
                placeholder="选择标签"
                multiple
                clearable
                @change="handleFilterChange"
                class="w-full"
              >
                <el-option
                  v-for="tag in availableTags"
                  :key="tag"
                  :label="tag"
                  :value="tag"
                />
              </el-select>
            </div>
          </div>
        </div>
      </el-collapse-transition>
    </div>

    <!-- 结果统计和推荐标签 -->
    <div v-if="searchResults.items && searchResults.items.length > 0" class="results-header mt-6">
      <div class="flex justify-between items-start">
        <p class="text-lg font-medium">
          找到 <span class="text-blue-600 font-bold">{{ searchResults.total }}</span> 张相关照片
        </p>
        <div v-if="searchResults.suggested_tags.length > 0" class="suggested-tags">
          <span class="text-sm text-gray-600 mr-2">推荐标签:</span>
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
            <div class="mt-4">
              <span class="text-sm text-gray-600 mr-2">示例搜索:</span>
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
        <el-empty description="未找到相关照片" />
      </div>

      <!-- 有结果网格 -->
      <div v-else class="photo-grid">
        <div
          v-for="photo in searchResults.items"
          :key="photo.id"
          class="photo-card"
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
          </div>
          <div class="photo-info">
            <p class="photo-name truncate text-sm font-medium">
              {{ photo.original_name || '未命名' }}
            </p>
            <p v-if="photo.city" class="photo-city text-xs text-gray-500">
              {{ photo.city }}
            </p>
            <p v-if="photo.photo_time" class="photo-time text-xs text-gray-500">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { loadAllPhotos, searchPhotos } from '@/api/search'
import { photoApi } from '@/api/photo'
import type { PhotoItem } from '@/types/photo'
import type { SearchRequest, SearchResponse } from '@/types/search'

// 搜索状态
const searchQuery = ref('')
const searchMode = ref<'semantic' | 'keyword' | 'tag'>('semantic')
const loading = ref(false)
const hasSearched = ref(false)
const showFilters = ref(false)

// 筛选条件
const filters = reactive({
  dateRange: null as [Date, Date] | null,
  city: '',
  tags: [] as string[],
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

// 可选城市和标签
const availableCities = ref<string[]>([])
const availableTags = ref<string[]>([])

// 示例查询
const exampleQueries = ['风景', '人物', '美食', '建筑']

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
        city: filters.city || undefined,
        tags: filters.tags.length > 0 ? filters.tags : undefined,
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
  filters.city = ''
  filters.tags = []
  handleSearch()
}

/**
 * 选择示例查询
 */
function selectExampleQuery(query: string) {
  searchQuery.value = query
  searchMode.value = 'semantic'
  filters.dateRange = null
  filters.city = ''
  filters.tags = []
  handleSearch()
}

/**
 * 预览照片
 */
function previewPhoto(photo: any) {
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

    // 提取可用城市和标签（演示目的）
    const citiesSet = new Set<string>()
    const tagsSet = new Set<string>()

    allPhotos.forEach((photo) => {
      // 从 original_name 中提取标签
      if (photo.original_name) {
        const words = photo.original_name.split(/[-_\s]/).filter((w) => w.length > 2)
        words.forEach((word) => tagsSet.add(word))
      }
    })

    availableCities.value = Array.from(citiesSet).slice(0, 10)
    availableTags.value = Array.from(tagsSet).slice(0, 20)
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
  @apply bg-white rounded-lg shadow p-6;
}

.search-controls {
  @apply flex gap-4 items-center;

  .search-input {
    @apply flex-1;
  }

  .mode-buttons {
    @apply flex-shrink-0;
  }
}

.filter-toggle {
  @apply text-sm;
}

.filters-panel {
  @apply border border-gray-200;
}

.results-header {
  @apply bg-white rounded-lg shadow p-4;
}

.suggested-tags {
  @apply flex items-center flex-wrap gap-2;
}

.results-container {
  @apply bg-white rounded-lg shadow p-6;
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
    @apply w-full aspect-square bg-gray-200 rounded animate-pulse;
  }

  .skeleton-text {
    @apply h-4 bg-gray-200 rounded animate-pulse;
  }
}

.photo-grid {
  @apply grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4;
}

.photo-card {
  @apply bg-white rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer;

  .photo-container {
    @apply relative overflow-hidden bg-gray-100 aspect-square;

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
      @apply text-gray-900;
    }

    .photo-city,
    .photo-time {
      @apply text-gray-500;
    }

    .photo-tags {
      @apply flex flex-wrap gap-1;
    }
  }
}

.pagination {
  @apply bg-white rounded-lg shadow p-4;
}
</style>
