<template>
  <div class="flex flex-col h-full">
    <!-- 顶部信息栏 -->
    <div class="flex items-center justify-between mb-4 shrink-0">
      <h2 class="text-2xl font-bold text-gray-800 dark:text-dark-text">足迹地图</h2>
      <div class="flex items-center gap-4 text-sm text-gray-500 dark:text-dark-text-secondary">
        <span v-if="!loading">
          共 <strong class="text-gray-800 dark:text-dark-text">{{ locations.length }}</strong> 张照片有拍摄位置
        </span>
        <span v-if="cities.length > 0">
          覆盖 <strong class="text-gray-800 dark:text-dark-text">{{ cities.length }}</strong> 个城市
        </span>
        <span v-else-if="!loading && locations.length > 0">
          覆盖 <strong class="text-gray-800 dark:text-dark-text">{{ locations.length }}</strong> 个拍摄地点
        </span>
        <el-button
          v-if="!loading && locations.length > 0"
          size="small"
          :loading="backfilling"
          @click="handleGeocodeBackfill"
        >
          重新解析拍摄地点
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex-1 bg-gray-100 dark:bg-dark-hover rounded-xl animate-pulse flex items-center justify-center">
      <div class="text-center text-gray-400 dark:text-dark-text-secondary">
        <el-icon :size="48" class="mb-2"><Loading /></el-icon>
        <p>加载地图数据中...</p>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="locations.length === 0" class="flex-1 bg-gray-50 dark:bg-dark-hover rounded-xl flex items-center justify-center">
      <el-empty description="还没有带 GPS 信息的照片，上传照片时会自动提取拍摄位置">
        <el-button type="primary" @click="$router.push('/photos')">去上传照片</el-button>
      </el-empty>
    </div>

    <!-- 地图容器 -->
    <div v-else ref="mapContainer" class="flex-1 min-h-0 rounded-xl overflow-hidden shadow-sm border border-gray-200 dark:border-dark-border" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { mapApi } from '@/api/map'
import { taskApi } from '@/api/tasks'
import { photoApi } from '@/api/photo'
import { wgs84ToGcj02 } from '@/utils/coord'
import type { PhotoLocation } from '@/types/map'
// Leaflet 默认标记图标：打包后其自动探测的图片路径会失效导致标记不可见，
// 需显式导入图片资源交由 Vite 生成正确 URL。
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

const mapContainer = ref<HTMLElement | null>(null)
const loading = ref(true)
const backfilling = ref(false)
const locations = ref<PhotoLocation[]>([])

let mapInstance: any = null
let resizeObserver: ResizeObserver | null = null

// 统计去重城市数
const cities = computed(() => {
  const set = new Set<string>()
  locations.value.forEach((loc) => {
    if (loc.city) set.add(loc.city)
    else if (loc.province) set.add(loc.province)
  })
  return [...set]
})

function formatDate(dateStr?: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function buildPopupContent(loc: PhotoLocation): string {
  const thumbUrl = photoApi.thumbnailUrl(loc.id)
  const name = loc.original_name || '照片'
  const date = formatDate(loc.photo_time)
  const locationParts = [loc.country, loc.province, loc.city].filter(Boolean)
  const locationStr = locationParts.join(' · ')

  return `
    <div style="width:180px">
      <img src="${thumbUrl}" style="width:100%;height:120px;object-fit:cover;border-radius:6px 6px 0 0" />
      <div style="padding:8px 4px 4px">
        <div style="font-size:13px;font-weight:600;color:#333;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${name}">${name}</div>
        ${date ? `<div style="font-size:11px;color:#888;margin-top:2px">${date}</div>` : ''}
        ${locationStr ? `<div style="font-size:11px;color:#666;margin-top:2px">📍 ${locationStr}</div>` : ''}
      </div>
    </div>
  `
}

async function initMap() {
  if (!mapContainer.value || locations.value.length === 0) return

  // 动态导入 Leaflet，避免静态导入时的运行时问题
  // Leaflet 仅提供 UMD/CJS 构建，Vite 下命名空间上不会挂载插件运行时添加的
  // markerClusterGroup，必须取 default（即 leaflet 真正的导出对象）才能拿到插件方法。
  const leaflet = await import('leaflet')
  const L: any = (leaflet as any).default ?? leaflet
  // 标记聚合插件（副作用式扩展 L，需在 leaflet 之后导入）
  await import('leaflet.markercluster')

  // 修正默认标记图标路径（打包后自动探测会失效，导致标记不显示）
  delete (L.Icon.Default.prototype as any)._getIconUrl
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
  })

  // 初始化地图，默认中心设为中国
  mapInstance = L.map(mapContainer.value, {
    center: [35.0, 105.0],
    zoom: 4,
    zoomControl: true,
  })

  // 高德矢量路网瓦片（含注记），国内访问稳定
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    attribution: '&copy; 高德地图',
    maxZoom: 18,
    keepBuffer: 4, // 平移/缩放时保留更多缓冲瓦片，减少空白
    updateWhenZooming: false, // 缩放动画结束后再刷新瓦片，避免中间态留白
  }).addTo(mapInstance)

  // 添加标记点（GPS 为 WGS-84，需转换为高德 GCJ-02 避免偏移）
  // 使用标记聚合组：点位密集时自动合并为聚合圈，缩放展开
  const bounds = L.latLngBounds([])
  const clusterGroup = L.markerClusterGroup({
    maxClusterRadius: 50,
    showCoverageOnHover: false,
    chunkedLoading: true,
  })

  locations.value.forEach((loc) => {
    const [gcjLng, gcjLat] = wgs84ToGcj02(loc.longitude, loc.latitude)
    const marker = L.marker([gcjLat, gcjLng])
    marker.bindPopup(buildPopupContent(loc), {
      maxWidth: 220,
      className: 'photo-popup',
    })
    clusterGroup.addLayer(marker)
    bounds.extend([gcjLat, gcjLng])
  })

  mapInstance.addLayer(clusterGroup)

  // 自适应边界
  if (locations.value.length === 1) {
    const [gcjLng, gcjLat] = wgs84ToGcj02(locations.value[0].longitude, locations.value[0].latitude)
    mapInstance.setView([gcjLat, gcjLng], 12)
  } else {
    mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 })
  }

  // 监听容器尺寸变化（侧边栏折叠/窗口缩放），修正瓦片错位与空白
  resizeObserver = new ResizeObserver(() => {
    mapInstance?.invalidateSize()
  })
  resizeObserver.observe(mapContainer.value)
}

async function fetchLocations() {
  loading.value = true
  try {
    const res = await mapApi.getLocations()
    locations.value = res.data
  } catch (error) {
    console.error('[MapPage] 获取位置失败:', error)
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handleGeocodeBackfill() {
  backfilling.value = true
  try {
    const res = await taskApi.geocodeBackfill()
    const created = res.data?.created ?? 0
    if (created > 0) {
      ElMessage.success(`已创建 ${created} 个解析任务，稍后刷新可查看城市信息`)
    } else {
      ElMessage.info('没有需要重新解析的照片')
    }
  } catch (error) {
    console.error('[MapPage] 重新解析失败:', error)
    // handled by interceptor
  } finally {
    backfilling.value = false
  }
}

onMounted(async () => {
  await fetchLocations()
  // 等 DOM 更新后再初始化地图
  setTimeout(initMap, 0)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})
</script>

<style>
@import 'leaflet/dist/leaflet.css';
@import 'leaflet.markercluster/dist/MarkerCluster.css';
@import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

/* 自定义 popup 样式 */
.photo-popup .leaflet-popup-content-wrapper {
  padding: 0;
  border-radius: 8px;
  overflow: hidden;
}
.photo-popup .leaflet-popup-content {
  margin: 0;
}
.photo-popup .leaflet-popup-tip {
  box-shadow: none;
}
</style>
