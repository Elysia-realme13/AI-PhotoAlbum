import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { agentApi } from '@/api/agent'
import type { ChatMessage, Conversation } from '@/types/chat'

let messageIdCounter = 0
function nextId() {
  return `msg-${Date.now()}-${++messageIdCounter}`
}

// 会话消息内存持久化：无后端存储时，保存各会话消息以便切换时恢复
const sessionMessages = new Map<string, ChatMessage[]>()

export const useChatStore = defineStore('chat', () => {
  // ── 状态 ──
  const conversations = ref<Conversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const currentConversationId = ref<string | null>(null)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const loadingConversations = ref(false)
  const loadingMessages = ref(false)

  let cancelFn: (() => void) | null = null

  // ── 计算属性 ──
  const currentConversation = computed(() =>
    conversations.value.find((c) => c.id === currentConversationId.value) ?? null
  )

  // ── 加载对话列表 ──
  async function fetchConversations() {
    loadingConversations.value = true
    try {
      conversations.value = await agentApi.getConversations()
    } catch {
      // handled by caller
    } finally {
      loadingConversations.value = false
    }
  }

  // ── 加载对话消息（从内存会话恢复，无后端持久化） ──
  function fetchMessages(conversationId: string) {
    currentConversationId.value = conversationId
    messages.value = sessionMessages.get(conversationId) ?? []
  }

  // ── 发送消息 ──
  function sendMessage(query: string) {
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

    cancelFn = agentApi.sendMessage(
      { query, conversation_id: currentConversationId.value ?? undefined },
      // onChunk
      (chunk) => {
        streamingContent.value += chunk
        // 更新最后一条消息的内容
        const last = messages.value[messages.value.length - 1]
        if (last && last.streaming) {
          last.content = streamingContent.value
        }
      },
      // onDone
      (conversationId) => {
        const last = messages.value[messages.value.length - 1]
        if (last && last.streaming) {
          last.streaming = false
        }
        isStreaming.value = false
        streamingContent.value = ''
        cancelFn = null

        // 如果是新对话，更新 conversation_id
        if (!currentConversationId.value) {
          currentConversationId.value = conversationId
          // 推入对话列表
          conversations.value.unshift({
            id: conversationId,
            title: query.slice(0, 30) + (query.length > 30 ? '...' : ''),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            message_count: messages.value.length,
          })
        } else {
          // 更新已有对话的元信息
          const conv = conversations.value.find((c) => c.id === currentConversationId.value)
          if (conv) {
            conv.message_count = messages.value.length
            conv.updated_at = new Date().toISOString()
          }
        }

        // 持久化当前会话消息到内存（保存实时引用，后续追加自动同步）
        if (currentConversationId.value) {
          sessionMessages.set(currentConversationId.value, messages.value)
        }
      },
      // onError
      (error) => {
        const last = messages.value[messages.value.length - 1]
        if (last && last.streaming) {
          last.content = `抱歉，出错了：${error}`
          last.streaming = false
        }
        isStreaming.value = false
        streamingContent.value = ''
        cancelFn = null
      }
    )
  }

  // ── 中断生成 ──
  function cancelStream() {
    cancelFn?.()
    cancelFn = null
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
    // 先中断进行中的流，避免旧定时器写入已清空的消息列表
    cancelFn?.()
    cancelFn = null
    isStreaming.value = false
    streamingContent.value = ''
    currentConversationId.value = null
    messages.value = []
  }

  // ── 重置 ──
  function reset() {
    cancelFn?.()
    sessionMessages.clear()
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