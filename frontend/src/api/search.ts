import request from '@/utils/request'
import { photoApi } from '@/api/photo'
import type { PhotoItem } from '@/types/photo'
import type { SearchRequest, SearchResponse, SearchResultItem } from '@/types/search'

/** 本地搜索服务：语义搜索走后端，关键词/标签走前端本地过滤 */

let allPhotosCache: PhotoItem[] = []

/** 清除照片缓存（上传/删除后调用） */
export function clearPhotosCache() {
  allPhotosCache = []
}

/** 加载所有照片到本地（分页加载，避免单次请求超过后端限制） */
export async function loadAllPhotos(): Promise<PhotoItem[]> {
  if (allPhotosCache.length > 0) return allPhotosCache
  try {
    const allItems: PhotoItem[] = []
    let page = 1
    let hasMore = true

    while (hasMore) {
      const res = await photoApi.list({ page, page_size: 100 })
      const items = res.data.items || []
      allItems.push(...items)
      hasMore = items.length === 100
      page++
    }

    allPhotosCache = allItems
    return allPhotosCache
  } catch (error) {
    console.error('加载照片失败:', error)
    return []
  }
}

/** 后端语义搜索 API */
export const searchApi = {
  search(query: string, page = 1, pageSize = 20) {
    return request.post('/search', { query, page, page_size: pageSize })
  },
}

/** 检查文本是否包含关键词 */
function textMatches(text: string | undefined, keyword: string): boolean {
  if (!text) return false
  return text.toLowerCase().includes(keyword.toLowerCase())
}

/** 从 PhotoItem.tags（对象结构）提取标签文本数组，兼容旧的字符串数组结构 */
function toTagLabels(tags: PhotoItem['tags']): string[] {
  if (!tags) return []
  if (Array.isArray(tags)) {
    return tags
      .map((t) => (typeof t === 'string' ? t : (t as { label?: string })?.label))
      .filter((t): t is string => !!t)
  }
  return (tags.summary || [])
    .map((s) => s?.label)
    .filter((t): t is string => !!t)
}

/** 前端本地搜索（关键词/标签模式） */
export function searchPhotos(request: SearchRequest, allPhotos: PhotoItem[]): SearchResponse {
  const mode = request.mode || 'keyword'
  const page = Math.max(1, request.page || 1)
  const pageSize = Math.max(1, Math.min(request.page_size || 40, 200))
  const query = (request.query || '').trim()
  const filters = request.filters || {}

  let results: PhotoItem[] = []

  if (mode === 'keyword') {
    if (query) {
      const keywords = query.split(/\s+/).filter((k) => k.length > 0)
      results = allPhotos.filter((p) =>
        keywords.some((kw) => textMatches(p.original_name, kw))
      )
    } else {
      results = allPhotos
    }
    results.sort((a, b) => (b.upload_time || '') > (a.upload_time || '') ? -1 : 1)
  } else if (mode === 'tag') {
    if (query && query.trim()) {
      const tagQuery = query.toLowerCase().trim()
      results = allPhotos.filter((p) =>
        toTagLabels(p.tags).some((t) => t.toLowerCase().includes(tagQuery))
      )
    } else {
      results = allPhotos
    }
  }

  // 应用日期筛选
  if (filters.start_date || filters.end_date) {
    const start = filters.start_date ? new Date(filters.start_date) : null
    const end = filters.end_date ? new Date(filters.end_date) : null
    results = results.filter((p) => {
      if (!p.photo_time) return true
      const pTime = new Date(p.photo_time)
      if (start && pTime < start) return false
      if (end && pTime > end) return false
      return true
    })
  }

  // 提取推荐标签
  const suggestedTags: string[] = []
  const tagCounter: Record<string, number> = {}
  results.slice(0, 50).forEach((p) => {
    const labels = toTagLabels(p.tags)
    if (labels.length) {
      labels.forEach((tag) => {
        tagCounter[tag] = (tagCounter[tag] || 0) + 1
      })
    } else if (p.original_name) {
      const parts = p.original_name.split(/[-_\s]/).filter((x) => x.length > 2)
      parts.forEach((part) => {
        tagCounter[part] = (tagCounter[part] || 0) + 1
      })
    }
  })
  Object.entries(tagCounter)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([tag]) => suggestedTags.push(tag))

  // 分页
  const total = results.length
  const startIdx = (page - 1) * pageSize
  const endIdx = startIdx + pageSize
  const pageResults = results.slice(startIdx, endIdx)

  // 转换为 SearchResultItem
  const items: SearchResultItem[] = pageResults.map((p) => ({
    id: p.id,
    thumbnail_url: photoApi.thumbnailUrl(p.id),
    original_name: p.original_name,
    photo_time: p.photo_time ? new Date(p.photo_time).toISOString() : undefined,
    city: undefined,
    score: undefined,
    tags: toTagLabels(p.tags),
  }))

  return {
    items,
    total,
    query,
    mode,
    suggested_tags: suggestedTags,
  }
}
