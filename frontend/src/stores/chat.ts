import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { agentApi } from '@/api/agent'
import type { ChatMessage, Conversation } from '@/types/chat'

let messageIdCounter = 0
function nextId() {
  return `msg-${Date.now()}-${++messageIdCounter}`
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
        if (m.role === 'assistant') {
          if (typeof m.content === 'string') {
            try {
              const parsed = JSON.parse(m.content)
              content = parsed.text || m.content
            } catch {
              content = m.content as string
            }
          } else if (typeof m.content === 'object' && m.content !== null) {
            content = (m.content as { text?: string }).text || ''
          }
        } else {
          content = typeof m.content === 'string' ? m.content : JSON.stringify(m.content)
        }
        return {
          id: String(m.id),
          role: m.role as 'user' | 'assistant',
          content,
          created_at: m.created_at,
        }
      })
    } catch {
      // handled by interceptor
    } finally {
      loadingMessages.value = false
    }
  }

  // ── 发送消息 ──
  async function sendMessage(query: string) {
    if (!query.trim() || isStreaming.value) return

    // 添加用户消息
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
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
      const res = await agentApi.sendMessage(currentConversationId.value, query)
      const reply = res.data.reply

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

  // ── 重置 ──
  function reset() {
    conversations.value = []
    messages.value = []
    currentConversationId.value = null
    isStreaming.value = false
    streamingContent.value = ''
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
    reset,
  }
})
