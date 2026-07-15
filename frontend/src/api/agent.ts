import type { ChatRequest, ChatMessage, Conversation } from '@/types/chat'
import type { PhotoItem } from '@/types/photo'
import type { PhotoLocation } from '@/types/map'
import { loadAllPhotos } from '@/api/search'
import { mapApi } from '@/api/map'

// ── 说明 ──────────────────────────────────────────────
// 后端 Agent 接口尚未就绪（backend/app/api/agent.py 为 TODO）。
// 此处为纯前端实现：基于真实照片数据（/api/photos 与 /api/photos/locations）
// 解析用户意图并生成回复，不再返回任何捏造的照片数量或内容。

// ── 工具：安全获取 GPS 位置（失败降级为空） ──
async function fetchLocationsSafe(): Promise<PhotoLocation[]> {
  try {
    const res = await mapApi.getLocations()
    return res.data || []
  } catch {
    return []
  }
}

// ── 工具：从照片时间取年份（优先 photo_time，回退 upload_time） ──
function photoYear(p: PhotoItem): string | null {
  const t = p.photo_time || p.upload_time
  if (!t) return null
  const d = new Date(t)
  return Number.isNaN(d.getTime()) ? null : String(d.getFullYear())
}

// ── 工具：统计分布（key -> 数量，按数量降序） ──
function distribution(items: (string | null | undefined)[]): [string, number][] {
  const counter: Record<string, number> = {}
  for (const key of items) {
    if (!key) continue
    counter[key] = (counter[key] || 0) + 1
  }
  return Object.entries(counter).sort((a, b) => b[1] - a[1])
}

// ── 意图识别 ──
type Intent = 'location' | 'time' | 'search' | 'overview' | 'help'

function detectIntent(query: string): Intent {
  const q = query.toLowerCase()
  const has = (kws: string[]) => kws.some((k) => q.includes(k))

  if (has(['你好', 'hello', 'hi', '在吗', '能做什么', '帮助', '怎么用', '功能'])) {
    return 'help'
  }
  if (has(['位置', '地点', '足迹', '在哪', '哪里', '城市', '地方', '地图', '省', 'gps'])) {
    return 'location'
  }
  if (has(['时间', '什么时候', '哪天', '日期', '几月', '年份', '最近', '最早', '哪年', '哪一年'])) {
    return 'time'
  }
  if (has(['多少', '几张', '数量', '统计', '总共', '一共', '概览', '情况', '总数', '分布'])) {
    return 'overview'
  }
  if (has(['找', '搜', '查', '有没有', '筛选'])) {
    return 'search'
  }
  return 'overview'
}

// ── 回复构建器 ──

function buildHelp(total: number): string {
  return `你好！我是 AI 智能相册助手。你的相册目前共有 **${total}** 张照片。

我可以帮你：

1. **统计概览** — “我的相册有多少张照片？”
2. **时间分布** — “这些照片都是哪年拍的？”
3. **位置足迹** — “我在哪些城市拍过照片？”
4. **按名称搜索** — “帮我找一下 sunset 的照片”

> 说明：当前基于你相册中的真实数据作答，暂不支持内容识别与自动整理（后端 AI 能力开发中）。

告诉我你想了解什么吧？`
}

function buildOverview(photos: PhotoItem[], locations: PhotoLocation[]): string {
  const total = photos.length
  const years = distribution(photos.map(photoYear))
  const types = distribution(photos.map((p) => p.file_type))
  const withGps = locations.length

  let md = `你的相册目前共有 **${total}** 张照片。\n\n`

  if (years.length > 0) {
    md += `### 按年份分布\n`
    for (const [year, count] of years) {
      md += `- ${year} 年：${count} 张\n`
    }
    md += `\n`
  }

  if (types.length > 0) {
    md += `### 按格式分布\n`
    for (const [type, count] of types) {
      md += `- ${type.toUpperCase()}：${count} 张\n`
    }
    md += `\n`
  }

  md += `### 位置信息\n`
  if (withGps > 0) {
    md += `- 有 **${withGps}** 张照片包含 GPS 坐标，可在“足迹”页查看地图。\n`
  } else {
    md += `- 暂无包含 GPS 坐标的照片，足迹地图为空。\n`
  }

  return md.trim()
}

function buildTime(photos: PhotoItem[]): string {
  const total = photos.length
  const years = distribution(photos.map(photoYear))

  if (years.length === 0) {
    return `你的相册里共有 **${total}** 张照片，但都缺少拍摄时间（EXIF）信息，无法按时间统计。`
  }

  // 按年份从早到晚排序展示
  const sortedByYear = [...years].sort((a, b) => Number(a[0]) - Number(b[0]))
  let md = `你的相册照片按拍摄时间分布如下：\n\n`
  for (const [year, count] of sortedByYear) {
    md += `- **${year} 年**：${count} 张\n`
  }
  const earliest = sortedByYear[0][0]
  const latest = sortedByYear[sortedByYear.length - 1][0]
  md += `\n时间跨度：${earliest} 年 ~ ${latest} 年。`
  return md
}

function buildLocation(locations: PhotoLocation[]): string {
  if (locations.length === 0) {
    return `你的相册里暂时没有包含 GPS 坐标的照片，所以无法生成位置足迹。

如果希望使用足迹地图，请上传带有 GPS 信息（EXIF）的照片。`
  }

  const cities = distribution(locations.map((l) => l.city))
  const provinces = distribution(locations.map((l) => l.province))

  let md = `共有 **${locations.length}** 张照片带有 GPS 坐标。\n\n`

  if (cities.length > 0) {
    md += `### 按城市分布\n`
    for (const [city, count] of cities) {
      md += `- ${city}：${count} 张\n`
    }
    md += `\n`
  } else if (provinces.length > 0) {
    md += `### 按省份分布\n`
    for (const [province, count] of provinces) {
      md += `- ${province}：${count} 张\n`
    }
    md += `\n`
  } else {
    md += `这些照片有坐标但暂未解析出城市名称，可在“足迹”页地图上查看具体位置。\n`
  }

  md += `你可以打开“足迹”页在地图上查看这些照片的分布。`
  return md.trim()
}

// 从查询中剥离意图词，提取搜索关键词
function extractKeywords(query: string): string[] {
  const stopWords = ['帮我', '找一下', '找', '搜索', '搜', '查', '一下', '有没有', '的', '照片', '图片', '相册', '请', '我', '想']
  let q = query
  for (const w of stopWords) q = q.split(w).join(' ')
  return q
    .split(/\s+/)
    .map((k) => k.trim())
    .filter((k) => k.length > 0)
}

function buildSearch(photos: PhotoItem[], query: string): string {
  const keywords = extractKeywords(query)

  if (keywords.length === 0) {
    return `请告诉我想搜索的关键词，例如“帮我找一下 sunset 的照片”。目前可按照片文件名进行匹配。`
  }

  const matched = photos.filter((p) => {
    const name = (p.original_name || p.filename || '').toLowerCase()
    return keywords.some((kw) => name.includes(kw.toLowerCase()))
  })

  if (matched.length === 0) {
    return `没有找到文件名匹配 “${keywords.join(' ')}” 的照片。

> 提示：当前仅支持按文件名匹配，内容/标签语义搜索需后端 AI 能力（开发中）。`
  }

  let md = `按文件名匹配到 **${matched.length}** 张与 “${keywords.join(' ')}” 相关的照片：\n\n`
  for (const p of matched.slice(0, 8)) {
    const name = p.original_name || p.filename
    const year = photoYear(p)
    md += `- ${name}${year ? `（${year} 年）` : ''}\n`
  }
  if (matched.length > 8) {
    md += `- ……以及其它 ${matched.length - 8} 张\n`
  }
  md += `\n可前往“搜索”页做更精细的筛选。`
  return md
}

// ── 根据意图组装回复 ──
function buildReply(query: string, photos: PhotoItem[], locations: PhotoLocation[]): string {
  const total = photos.length

  if (total === 0) {
    return `你的相册目前还没有照片。

上传照片后，我可以帮你统计数量、分析拍摄时间与位置分布。`
  }

  const intent = detectIntent(query)
  switch (intent) {
    case 'help':
      return buildHelp(total)
    case 'location':
      return buildLocation(locations)
    case 'time':
      return buildTime(photos)
    case 'search':
      return buildSearch(photos, query)
    case 'overview':
    default:
      return buildOverview(photos, locations)
  }
}

// ── 逐字流式输出（保留原有打字机效果） ──
function streamText(
  text: string,
  onChunk: (chunk: string) => void,
  onDone: (conversationId: string) => void
): () => void {
  let index = 0
  let cancelled = false

  const timer = setInterval(() => {
    if (cancelled) {
      clearInterval(timer)
      return
    }
    if (index < text.length) {
      const step = Math.floor(Math.random() * 3) + 1
      const chars = text.slice(index, index + step)
      index += chars.length
      onChunk(chars)
    } else {
      clearInterval(timer)
      onDone(`conv-${Date.now()}`)
    }
  }, 20)

  return () => {
    cancelled = true
    clearInterval(timer)
  }
}

export const agentApi = {
  /**
   * 发送消息：基于真实照片数据生成回复并流式输出。
   * 返回 cancel 函数，可在加载阶段或流式阶段中断。
   */
  sendMessage(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
    onDone: (conversationId: string) => void,
    onError: (error: string) => void
  ): () => void {
    let cancelled = false
    let stopStream: (() => void) | null = null

    void (async () => {
      try {
        const [photos, locations] = await Promise.all([loadAllPhotos(), fetchLocationsSafe()])
        if (cancelled) return
        const reply = buildReply(request.query || '', photos, locations)
        if (cancelled) return
        stopStream = streamText(reply, onChunk, onDone)
      } catch {
        if (!cancelled) onError('加载相册数据失败，请稍后重试')
      }
    })()

    return () => {
      cancelled = true
      stopStream?.()
    }
  },

  /**
   * 获取对话列表。
   * 无后端持久化，返回空列表（会话仅在本次会话内存中维护）。
   */
  async getConversations(): Promise<Conversation[]> {
    return []
  },

  /**
   * 获取对话消息。
   * 无后端持久化，历史消息由前端 store 在内存中保存。
   */
  async getMessages(_conversationId: string): Promise<ChatMessage[]> {
    return []
  },
}
