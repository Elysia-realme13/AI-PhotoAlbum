<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text mb-6">首页</h2>

    <!-- 加载骨架屏 -->
    <div v-if="loading">
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div v-for="i in 4" :key="i" class="bg-white dark:bg-dark-card rounded-xl p-5 shadow-sm border border-gray-100 dark:border-dark-border">
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="h-3 bg-gray-200 dark:bg-dark-hover rounded w-16 mb-3 animate-pulse" />
              <div class="h-8 bg-gray-200 dark:bg-dark-hover rounded w-12 animate-pulse" />
            </div>
            <div class="w-12 h-12 rounded-lg bg-gray-200 dark:bg-dark-hover animate-pulse" />
          </div>
        </div>
      </div>
      <div class="bg-white dark:bg-dark-card rounded-xl shadow-sm border border-gray-100 dark:border-dark-border p-5">
        <div class="h-5 bg-gray-200 dark:bg-dark-hover rounded w-24 mb-4 animate-pulse" />
        <div class="grid grid-cols-6 gap-3">
          <div v-for="i in 6" :key="i" class="aspect-square bg-gray-200 dark:bg-dark-hover rounded-lg animate-pulse" />
        </div>
      </div>
    </div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-white dark:bg-dark-card rounded-xl p-5 shadow-sm border border-gray-100 dark:border-dark-border hover-scale cursor-pointer" @click="router.push('/photos')">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 dark:text-dark-text-secondary text-sm">总照片数</p>
              <p class="text-3xl font-bold text-gray-800 dark:text-dark-text mt-1">{{ stats.photos }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
              <el-icon :size="24" color="#409EFF"><PictureFilled /></el-icon>
            </div>
          </div>
        </div>
        <div class="bg-white dark:bg-dark-card rounded-xl p-5 shadow-sm border border-gray-100 dark:border-dark-border hover-scale cursor-pointer" @click="router.push('/albums')">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 dark:text-dark-text-secondary text-sm">相册数</p>
              <p class="text-3xl font-bold text-gray-800 dark:text-dark-text mt-1">{{ stats.albums }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-green-50 dark:bg-green-900/30 flex items-center justify-center">
              <el-icon :size="24" color="#67C23A"><Folder /></el-icon>
            </div>
          </div>
        </div>
        <div class="bg-white dark:bg-dark-card rounded-xl p-5 shadow-sm border border-gray-100 dark:border-dark-border hover-scale cursor-pointer" @click="router.push('/faces')">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 dark:text-dark-text-secondary text-sm">识别人物</p>
              <p class="text-3xl font-bold text-gray-800 dark:text-dark-text mt-1">{{ stats.faces ?? '--' }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center">
              <el-icon :size="24" color="#9C27B0"><UserFilled /></el-icon>
            </div>
          </div>
        </div>
        <div class="bg-white dark:bg-dark-card rounded-xl p-5 shadow-sm border border-gray-100 dark:border-dark-border hover-scale cursor-pointer" @click="router.push('/map')">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-500 dark:text-dark-text-secondary text-sm">{{ stats.cities > 0 ? '足迹城市' : '拍摄地点' }}</p>
              <p class="text-3xl font-bold text-gray-800 dark:text-dark-text mt-1">{{ stats.cities > 0 ? stats.cities : stats.locations }}</p>
            </div>
            <div class="w-12 h-12 rounded-lg bg-orange-50 dark:bg-orange-900/30 flex items-center justify-center">
              <el-icon :size="24" color="#E6A23C"><Location /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近上传（左） + 拍摄热度/月度统计叠放（右） -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <!-- 左：最近上传 -->
        <div
          class="bg-white dark:bg-dark-card rounded-xl shadow-sm border border-gray-100 dark:border-dark-border p-5"
          :class="{ 'lg:col-span-2': heatmapData.length === 0 }"
        >
          <h3 class="text-lg font-semibold text-gray-800 dark:text-dark-text mb-4">最近上传</h3>
          <el-empty v-if="recentPhotos.length === 0" description="还没有照片，快去上传吧！" />
          <div v-else class="grid grid-cols-3 gap-3">
            <div
              v-for="(photo, index) in recentPhotos"
              :key="photo.id"
              class="group relative aspect-square bg-gray-100 dark:bg-dark-hover rounded-lg overflow-hidden cursor-pointer"
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

        <!-- 右：拍摄热度 / 月度统计（合并卡片，按钮切换） -->
        <div v-if="heatmapData.length > 0" class="bg-white dark:bg-dark-card rounded-xl shadow-sm border border-gray-100 dark:border-dark-border p-5">
          <div class="flex items-center justify-between mb-4">
            <el-segmented v-model="viewMode" :options="segmentOptions" size="small" />
            <el-date-picker
              v-if="viewMode === 'calendar'"
              v-model="selectedMonth"
              type="month"
              value-format="YYYY-MM"
              :clearable="false"
              placeholder="选择月份"
              size="small"
              style="width: 130px"
            />
            <el-date-picker
              v-else
              v-model="selectedYear"
              type="year"
              value-format="YYYY"
              :clearable="false"
              placeholder="选择年份"
              size="small"
              style="width: 110px"
            />
          </div>

          <div class="min-h-[300px]">
            <!-- 简约日历网格（微软日历风） -->
            <div v-if="viewMode === 'calendar'">
              <div class="grid grid-cols-7 gap-1 mb-1">
                <div
                  v-for="w in weekLabels"
                  :key="w"
                  class="text-center text-xs text-gray-400 dark:text-dark-text-secondary py-1"
                >
                  {{ w }}
                </div>
              </div>
              <div class="grid grid-cols-7 gap-1">
                <template v-for="(week, wi) in calendarWeeks" :key="wi">
                  <div
                    v-for="(cell, ci) in week"
                    :key="ci"
                    class="relative h-9 rounded-md flex items-center justify-center text-xs text-slate-800 dark:text-dark-text"
                    :class="{ 'ring-1 ring-blue-400': cell?.isToday }"
                    :style="cell ? cellStyle(cell.count) : {}"
                    :title="cell ? cell.date + '：' + cell.count + ' 张' : ''"
                  >
                    <template v-if="cell">
                      {{ cell.day }}
                      <span
                        v-if="cell.count > 0"
                        class="absolute bottom-0.5 right-1 text-[10px] text-blue-600"
                      >{{ cell.count }}</span>
                    </template>
                  </div>
                </template>
              </div>
            </div>

            <!-- 月度拍摄统计柱状图 -->
            <v-chart
              v-else
              :option="barOption"
              autoresize
              class="w-full"
              style="height: 260px"
              @click="handleBarClick"
            />
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
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { InfoFilled } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { photoApi } from '@/api/photo'
import { albumApi } from '@/api/album'
import { mapApi } from '@/api/map'
import { faceApi } from '@/api/face'
import { useThemeStore } from '@/stores/theme'
import PhotoDetailDrawer from '@/components/photo/PhotoDetailDrawer.vue'
import type { PhotoItem } from '@/types/photo'

// 注册 ECharts 组件
use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const router = useRouter()
const themeStore = useThemeStore()

const loading = ref(true)

const stats = ref({
  photos: 0,
  albums: 0,
  faces: null as number | null,
  cities: 0,
  locations: 0,
})

const recentPhotos = ref<PhotoItem[]>([])

// ── 拍摄热度（可选月份日历热力图）─────────────
const heatmapData = ref<[string, number][]>([])

// 选中月份 'YYYY-MM'，默认当前月，加载数据后定位到最新有照片的月份
const selectedMonth = ref<string>(
  `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
)
// 柱状图选中年份（可独立于日历月份切换）
const selectedYear = ref<string>(selectedMonth.value.slice(0, 4))

const monthLabels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

// ── 视图切换：拍摄热度日历 / 月度统计柱状图 ─────
type HeatView = 'calendar' | 'bar'
const viewMode = ref<HeatView>('calendar')
const segmentOptions = [
  { label: '拍摄热度', value: 'calendar' },
  { label: '月度统计', value: 'bar' },
]

// 切到月度统计时，默认落在当前日历上下文的年份
watch(viewMode, (mode) => {
  if (mode === 'bar') selectedYear.value = selectedMonth.value.slice(0, 4)
})

// 日历表头（周一开头）
const weekLabels = ['一', '二', '三', '四', '五', '六', '日']

interface CalendarCell {
  date: string
  day: number
  count: number
  isToday: boolean
}

// 按周分组生成所选月份的日历网格（周一开头，前导/末尾空位补 null）
const calendarWeeks = computed<(CalendarCell | null)[][]>(() => {
  const [y, m] = selectedMonth.value.split('-').map(Number)
  if (!y || !m) return []
  const daysInMonth = new Date(y, m, 0).getDate()
  const leading = (new Date(y, m - 1, 1).getDay() + 6) % 7 // 周一开头的前导空位
  const map = new Map(heatmapData.value)
  const now = new Date()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

  const cells: (CalendarCell | null)[] = []
  for (let i = 0; i < leading; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${selectedMonth.value}-${String(d).padStart(2, '0')}`
    cells.push({ date, day: d, count: map.get(date) || 0, isToday: date === todayStr })
  }
  while (cells.length % 7 !== 0) cells.push(null)

  const weeks: (CalendarCell | null)[][] = []
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))
  return weeks
})

// 当月单日最大照片数，用于着色归一化
const monthMax = computed(() => {
  let max = 0
  for (const week of calendarWeeks.value) {
    for (const cell of week) {
      if (cell && cell.count > max) max = cell.count
    }
  }
  return max
})

// 有照片的格子按数量轻微着色（数字保持深色，观感简约）
function cellStyle(count: number) {
  if (count <= 0) return {}
  const alpha = 0.12 + 0.5 * (count / (monthMax.value || 1))
  return { backgroundColor: `rgba(59,130,246,${alpha})` }
}

// ── 月度柱状图 ─────
const monthlyTotals = computed(() => {
  const totals = new Array(12).fill(0)
  for (const [date, count] of heatmapData.value) {
    if (date.slice(0, 4) !== selectedYear.value) continue
    const month = Number(date.slice(5, 7))
    if (month >= 1 && month <= 12) totals[month - 1] += count
  }
  return totals
})

const barOption = computed(() => {
  const dark = themeStore.theme === 'dark'
  const axisText = dark ? '#94a3b8' : '#606266'
  const axisLine = dark ? '#2a2a4a' : '#e0e0e0'
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: Array<{ dataIndex: number; value: number }>) => {
        const p = params[0]
        return `${monthLabels[p.dataIndex]}：${p.value} 张`
      },
    },
    grid: { top: 20, left: 10, right: 20, bottom: 10, containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisTick: { show: false },
      axisLabel: { color: axisText },
      axisLine: { lineStyle: { color: axisLine } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: axisText },
      splitLine: { lineStyle: { color: axisLine } },
    },
    series: [
      {
        type: 'bar',
        data: monthlyTotals.value,
        itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 28,
      },
    ],
  }
})

// 点击柱子切换到对应月份，与日历联动
function handleBarClick(params: { dataIndex: number }) {
  const month = String(params.dataIndex + 1).padStart(2, '0')
  selectedMonth.value = `${selectedYear.value}-${month}`
  viewMode.value = 'calendar'
}

/** 分页拉取用于热度图的照片（后端 page_size 上限 200，此处分页并限制上限避免过多请求） */
async function fetchHeatmapPhotos(): Promise<PhotoItem[]> {
  const pageSize = 200
  const first = await photoApi.list({ page: 1, page_size: pageSize, sort_by: 'photo_time', order: 'desc' })
  const items: PhotoItem[] = [...first.data.items]
  const totalPages = Math.min(Math.ceil((first.data.total || 0) / pageSize), 10) // 最多 2000 张
  const rest = []
  for (let p = 2; p <= totalPages; p++) {
    rest.push(photoApi.list({ page: p, page_size: pageSize, sort_by: 'photo_time', order: 'desc' }))
  }
  const resList = await Promise.all(rest)
  for (const r of resList) items.push(...r.data.items)
  return items
}

/** 按日期聚合照片数量（优先拍摄时间，回退上传时间） */
function buildHeatmap(photos: PhotoItem[]) {
  const counter = new Map<string, number>()
  for (const p of photos) {
    const raw = p.photo_time || p.upload_time
    if (!raw) continue
    const date = raw.slice(0, 10) // YYYY-MM-DD
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue
    counter.set(date, (counter.get(date) || 0) + 1)
  }
  const entries: [string, number][] = [...counter.entries()]
  heatmapData.value = entries
  // 默认定位到数据中最新有照片的月份
  if (entries.length > 0) {
    const months = entries.map(([d]) => d.slice(0, 7)).sort()
    selectedMonth.value = months[months.length - 1]
    selectedYear.value = selectedMonth.value.slice(0, 4)
  }
}

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
    const [statsRes, recentRes, locationsRes, albumsRes, facesRes, heatmapPhotos] = await Promise.all([
      photoApi.list({ page: 1, page_size: 1 }),
      photoApi.list({ page: 1, page_size: 6, sort_by: 'upload_time', order: 'desc' }),
      mapApi.getLocations(),
      albumApi.list(),
      faceApi.listIdentities(),
      fetchHeatmapPhotos(),
    ])
    stats.value.photos = statsRes.data.total
    stats.value.albums = Array.isArray(albumsRes.data) ? albumsRes.data.length : 0
    stats.value.faces = Array.isArray(facesRes.data) ? facesRes.data.length : 0
    recentPhotos.value = recentRes.data.items
    buildHeatmap(heatmapPhotos || [])
    // 与足迹页相同的去重逻辑：优先用 city，回退 province
    const citySet = new Set<string>()
    for (const loc of locationsRes.data || []) {
      if (loc.city) citySet.add(loc.city)
      else if (loc.province) citySet.add(loc.province)
    }
    stats.value.cities = citySet.size
    // 无城市解析结果时回退展示有位置的照片数，避免误导为 0
    stats.value.locations = (locationsRes.data || []).length
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
