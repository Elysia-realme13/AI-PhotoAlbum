import { photoApi } from '@/api/photo'
import type { PhotoItem } from '@/types/photo'
import type { SearchRequest, SearchResponse, SearchResultItem, SearchMode } from '@/types/search'

/** 本地搜索服务：调用后端照片 API + 前端本地过滤/排序 */

let allPhotosCache: PhotoItem[] = []

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
      // 如果返回项数少于 page_size，说明已到最后一页
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

/** 生成伪造的相似度分数 */
function generateScore(): number {
  return Math.random() * 0.35 + 0.6 // 0.6 ~ 0.95
}

/** 检查文本是否包含关键词 */
function textMatches(text: string | undefined, keyword: string): boolean {
  if (!text) return false
  return text.toLowerCase().includes(keyword.toLowerCase())
}

/** 根据 query 计算匹配得分 */
function calculateSemanticScore(photo: PhotoItem, query: string): number {
  if (!query) return 0
  const keywords = query.split(/\s+/).filter((k) => k.length > 0)
  let matchCount = 0
  const checkText = (text: string | undefined) => {
    for (const kw of keywords) {
      if (textMatches(text, kw)) matchCount++
    }
  }
  checkText(photo.original_name)
  // 注：PhotoItem 默认无 tags/description，仅用 original_name 作为演示
  return matchCount > 0 ? generateScore() : 0
}

/** 前端本地搜索 */
export function searchPhotos(request: SearchRequest, allPhotos: PhotoItem[]): SearchResponse {
  const mode = request.mode || 'semantic'
  const page = Math.max(1, request.page || 1)
  const pageSize = Math.max(1, Math.min(request.page_size || 40, 200))
  const query = (request.query || '').trim()
  const filters = request.filters || {}

  let results: (PhotoItem & { score?: number })[] = []

  // 第一步：按模式搜索
  if (mode === 'semantic') {
    // 语义模式（模拟）：根据 query 在 original_name 中做模糊匹配
    if (query) {
      results = allPhotos
        .map((p) => ({
          ...p,
          score: calculateSemanticScore(p, query),
        }))
        .filter((p) => p.score! > 0)
        .sort((a, b) => (b.score || 0) - (a.score || 0))
    } else {
      results = allPhotos.map((p) => ({ ...p, score: 0 }))
    }
  } else if (mode === 'keyword') {
    // 关键词模式：匹配 original_name
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
    // 标签模式：这里简化处理，因为 PhotoItem 默认无 tags
    // 实际应用需要后端返回 tags 或前端维护 tags 映射
    results = allPhotos
  }

  // 第二步：应用筛选条件
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

  if (filters.city) {
    // PhotoMetadata 在后端；这里简化处理
    // 实际应用需要后端返回或前端维护 city 映射
  }

  if (filters.tags && filters.tags.length > 0) {
    // 标签过滤：因 PhotoItem 默认无 tags，此处为占位
  }

  // 第三步：提取推荐标签（从结果集的 original_name 分词）
  const suggestedTags: string[] = []
  const tagCounter: Record<string, number> = {}
  results.slice(0, 50).forEach((p) => {
    if (p.original_name) {
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

  // 第四步：分页
  const total = results.length
  const start = (page - 1) * pageSize
  const end = start + pageSize
  const pageResults = results.slice(start, end)

  // 第五步：转换为 SearchResultItem
  const items: SearchResultItem[] = pageResults.map((p) => ({
    id: p.id,
    thumbnail_url: photoApi.thumbnailUrl(p.id),
    original_name: p.original_name,
    photo_time: p.photo_time ? new Date(p.photo_time).toISOString() : undefined,
    city: undefined, // 示例：无 city 数据
    score: p.score,
    tags: [], // 示例：无 tags 数据
  }))

  return {
    items,
    total,
    query,
    mode,
    suggested_tags: suggestedTags,
  }
}
