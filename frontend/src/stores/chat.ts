import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { agentApi } from '@/api/agent'
import type { ChatMessage, Conversation, CandidateCluster } from '@/types/chat'

let messageIdCounter = 0
function nextId() {
  return `msg-${Date.now()}-${++messageIdCounter}`
}

/**
 * 从用户输入中提取可能的中文人名（2-4个汉字，排除常见动词/名词）
 * 简单启发式：取第一个连续中文片段（2-4字）作为候选人名
 */
function extractPersonName(query: string): string {
  // 匹配连续中文字符片段（2-4字）
  const match = query.match(/[\u4e00-\u9fa5]{2,4}/)
  if (!match) return ''
  const candidate = match[0]
  // 排除常见非人名词汇
  const exclude = ['照片', '相册', '风景', '旅游', '海边', '夏天', '去年', '最近', '分析', '整理', '生成', '帮我', '找一', '一下', '创建', '精彩', '回顾']
  if (exclude.some(w => candidate.includes(w) || w.includes(candidate))) return ''
  return candidate
}

export const useChatStore = defineStore('chat', () => {
  // ── 状态 ──
  const conversations = ref<Conversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const currentConversationId = ref<string | null>(null)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const loadingConversations = ref(false)
  const loadingMessages = ref(false)

  // ── 计算属性 ──
  const currentConversation = computed(() =>
    conversations.value.find((c) => c.id === currentConversationId.value) ?? null
  )

  // ── 加载对话列表 ──
  async function fetchConversations() {
    loadingConversations.value = true
    try {
      const res = await agentApi.getConversations()
      conversations.value = res.data.map((s) => ({
        id: s.id,
        title: s.title,
        message_count: s.message_count,
        created_at: s.created_at,
        updated_at: s.updated_at,
      }))
    } catch {
      // handled by interceptor
    } finally {
      loadingConversations.value = false
    }
  }

  // ── 加载对话消息 ──
  async function fetchMessages(conversationId: string) {
    currentConversationId.value = conversationId
    loadingMessages.value = true
    try {
      const res = await agentApi.getMessages(conversationId)
      messages.value = res.data.map((m) => {
        // 后端 assistant 消息的 content 是 JSON {text, results, total}
        let content = ''
        let results: { photo_id: string; score: number }[] | undefined
        if (m.role === 'assistant') {
          let parsed: unknown = null
          if (typeof m.content === 'string') {
            try {
              parsed = JSON.parse(m.content)
              content = (parsed as { text?: string }).text || m.content
            } catch {
              content = m.content as string
            }
          } else if (typeof m.content === 'object' && m.content !== null) {
            parsed = m.content
            content = (m.content as { text?: string }).text || ''
          }
          if (parsed && typeof parsed === 'object' && Array.isArray((parsed as { results?: unknown }).results)) {
            results = (parsed as { results: { photo_id: string; score: number }[] }).results
          }
        } else {
          content = typeof m.content === 'string' ? m.content : JSON.stringify(m.content)
        }
        return {
          id: String(m.id),
          role: m.role as 'user' | 'assistant',
          content,
          created_at: m.created_at,
          results,
        }
      })
    } catch {
      messages.value = []
    } finally {
      loadingMessages.value = false
    }
  }

  // ── 发送消息 ──
  async function sendMessage(query: string, image?: File) {
    if (!query.trim() || isStreaming.value) return

    // 添加用户消息
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
      image: image,
      imageUrl: image ? URL.createObjectURL(image) : undefined,
    }
    messages.value.push(userMsg)

    // 创建临时 AI 消息占位
    const aiMsg: ChatMessage = {
      id: nextId(),
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      streaming: true,
    }
    messages.value.push(aiMsg)
    isStreaming.value = true
    streamingContent.value = ''

    try {
      // 若无当前会话，先创建
      if (!currentConversationId.value) {
        const sessionRes = await agentApi.createSession(query.slice(0, 50))
        currentConversationId.value = sessionRes.data.id
        // 推入对话列表
        conversations.value.unshift({
          id: sessionRes.data.id,
          title: sessionRes.data.title || query.slice(0, 30) + (query.length > 30 ? '...' : ''),
          message_count: 0,
          created_at: sessionRes.data.created_at,
          updated_at: sessionRes.data.updated_at,
        })
      }

      // 发送消息到后端
      const res = await agentApi.sendMessage(currentConversationId.value, query, image)
      const reply = res.data.reply
      const needsConfirmation = res.data.needs_confirmation
      const pendingCandidates = res.data.pending_candidates || []
      const photoResults = res.data.results || []

      // 提取人名（用于确认对话框）
      const personName = extractPersonName(query)

      // 前端模拟流式效果（逐字显示）
      let index = 0
      const streamTimer = setInterval(() => {
        if (index < reply.length) {
          const step = Math.floor(Math.random() * 3) + 1
          const chars = reply.slice(index, index + step)
          index += chars.length
          streamingContent.value += chars
          const last = messages.value[messages.value.length - 1]
          if (last && last.streaming) {
            last.content = streamingContent.value
          }
        } else {
          clearInterval(streamTimer)
          const last = messages.value[messages.value.length - 1]
          if (last && last.streaming) {
            last.streaming = false
            // 流式结束后附加检索到的照片结果
            if (photoResults.length > 0) {
              last.results = photoResults
            }
            // 流式结束后附加名称确认数据
            if (needsConfirmation && pendingCandidates.length > 0 && personName) {
              last.nameConfirm = {
                personName,
                candidates: pendingCandidates as unknown as CandidateCluster[],
                confirmed: false,
              }
            }
          }
          isStreaming.value = false
          streamingContent.value = ''

          // 更新对话元信息
          const conv = conversations.value.find((c) => c.id === currentConversationId.value)
          if (conv) {
            conv.message_count = (conv.message_count || 0) + 2
            conv.updated_at = new Date().toISOString()
          }
        }
      }, 20)
    } catch {
      const last = messages.value[messages.value.length - 1]
      if (last && last.streaming) {
        last.content = '抱歉，处理时出了点问题，请稍后重试。'
        last.streaming = false
      }
      isStreaming.value = false
      streamingContent.value = ''
    }
  }

  // ── 中断生成 ──
  function cancelStream() {
    const last = messages.value[messages.value.length - 1]
    if (last && last.streaming) {
      last.streaming = false
      if (!last.content) {
        last.content = '（已取消）'
      }
    }
    isStreaming.value = false
    streamingContent.value = ''
  }

  // ── 新建对话 ──
  function newConversation() {
    currentConversationId.value = null
    messages.value = []
    isStreaming.value = false
    streamingContent.value = ''
  }

  // ── 删除对话 ──
  async function deleteConversation(id: string) {
    await agentApi.deleteSession(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConversationId.value === id) {
      newConversation()
    }
  }

  // ── 重置 ──
  function reset() {
    conversations.value = []
    messages.value = []
    currentConversationId.value = null
    isStreaming.value = false
    streamingContent.value = ''
  }

  // ── 名称确认完成 ──
  function markNameConfirmed(messageId: string) {
    const msg = messages.value.find(m => m.id === messageId)
    if (msg && msg.nameConfirm) {
      msg.nameConfirm.confirmed = true
    }
  }

  // ── 名称确认跳过 ──
  function markNameSkipped(messageId: string) {
    const msg = messages.value.find(m => m.id === messageId)
    if (msg && msg.nameConfirm) {
      msg.nameConfirm = null
    }
  }

  return {
    conversations,
    messages,
    currentConversationId,
    isStreaming,
    streamingContent,
    loadingConversations,
    loadingMessages,
    currentConversation,
    fetchConversations,
    fetchMessages,
    sendMessage,
    cancelStream,
    newConversation,
    deleteConversation,
    markNameConfirmed,
    markNameSkipped,
    reset,
  }
})
