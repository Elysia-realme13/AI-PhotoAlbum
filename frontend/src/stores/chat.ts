import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { agentApi } from '@/api/agent'
import type { ChatMessage, Conversation, CandidateCluster } from '@/types/chat'

let messageIdCounter = 0
function nextId() {
  return `msg-${Date.now()}-${++messageIdCounter}`
}

/**
 * 浠庣敤鎴疯緭鍏ヤ腑鎻愬彇鍙兘鐨勪腑鏂囦汉鍚嶏紙2-4涓眽瀛楋紝鎺掗櫎甯歌鍔ㄨ瘝/鍚嶈瘝锛?
 * 绠€鍗曞惎鍙戝紡锛氬彇绗竴涓繛缁腑鏂囩墖娈碉紙2-4瀛楋級浣滀负鍊欓€変汉鍚?
 */
function extractPersonName(query: string): string {
  // 鍖归厤杩炵画涓枃瀛楃鐗囨锛?-4瀛楋級
  const match = query.match(/[\u4e00-\u9fa5]{2,4}/)
  if (!match) return ''
  const candidate = match[0]
  // 鎺掗櫎甯歌闈炰汉鍚嶈瘝姹?
  const exclude = ['鐓х墖', '鐩稿唽', '椋庢櫙', '鏃呮父', '娴疯竟', '澶忓ぉ', '鍘诲勾', '鏈€杩?, '鍒嗘瀽', '鏁寸悊', '鐢熸垚', '甯垜', '鎵句竴', '涓€涓?, '鍒涘缓', '绮惧僵', '鍥為【']
  if (exclude.some(w => candidate.includes(w) || w.includes(candidate))) return ''
  return candidate
}

export const useChatStore = defineStore('chat', () => {
  // 鈹€鈹€ 鐘舵€?鈹€鈹€
  const conversations = ref<Conversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const currentConversationId = ref<string | null>(null)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const loadingConversations = ref(false)
  const loadingMessages = ref(false)

  // 鈹€鈹€ 璁＄畻灞炴€?鈹€鈹€
  const currentConversation = computed(() =>
    conversations.value.find((c) => c.id === currentConversationId.value) ?? null
  )

  // 鈹€鈹€ 鍔犺浇瀵硅瘽鍒楄〃 鈹€鈹€
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

  // 鈹€鈹€ 鍔犺浇瀵硅瘽娑堟伅 鈹€鈹€
  async function fetchMessages(conversationId: string) {
    currentConversationId.value = conversationId
    loadingMessages.value = true
    try {
      const res = await agentApi.getMessages(conversationId)
      messages.value = res.data.map((m) => {
        // 鍚庣 assistant 娑堟伅鐨?content 鏄?JSON {text, results, total}
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

  // 鈹€鈹€ 鍙戦€佹秷鎭?鈹€鈹€
  async function sendMessage(query: string, image?: File) {
    if (!query.trim() || isStreaming.value) return

    // 娣诲姞鐢ㄦ埛娑堟伅
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
      image: image,
      imageUrl: image ? URL.createObjectURL(image) : undefined,
    }
    messages.value.push(userMsg)

    // 鍒涘缓涓存椂 AI 娑堟伅鍗犱綅
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
      // 鑻ユ棤褰撳墠浼氳瘽锛屽厛鍒涘缓
      if (!currentConversationId.value) {
        const sessionRes = await agentApi.createSession(query.slice(0, 50))
        currentConversationId.value = sessionRes.data.id
        // 鎺ㄥ叆瀵硅瘽鍒楄〃
        conversations.value.unshift({
          id: sessionRes.data.id,
          title: sessionRes.data.title || query.slice(0, 30) + (query.length > 30 ? '...' : ''),
          message_count: 0,
          created_at: sessionRes.data.created_at,
          updated_at: sessionRes.data.updated_at,
        })
      }

      // 鍙戦€佹秷鎭埌鍚庣
      const res = await agentApi.sendMessage(currentConversationId.value, query, image)
      const reply = res.data.reply
      const needsConfirmation = res.data.needs_confirmation
      const pendingCandidates = res.data.pending_candidates || []
      const photoResults = res.data.results || []

      // 鎻愬彇浜哄悕锛堢敤浜庣‘璁ゅ璇濇锛?
      const personName = extractPersonName(query)

      // 鍓嶇妯℃嫙娴佸紡鏁堟灉锛堥€愬瓧鏄剧ず锛?
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
            // 娴佸紡缁撴潫鍚庨檮鍔犳绱㈠埌鐨勭収鐗囩粨鏋?
            if (photoResults.length > 0) {
              last.results = photoResults
            }
            // 娴佸紡缁撴潫鍚庨檮鍔犲悕绉扮‘璁ゆ暟鎹?
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

          // 鏇存柊瀵硅瘽鍏冧俊鎭?
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
        last.content = '鎶辨瓑锛屽鐞嗘椂鍑轰簡鐐归棶棰橈紝璇风◢鍚庨噸璇曘€?
        last.streaming = false
      }
      isStreaming.value = false
      streamingContent.value = ''
    }
  }

  // 鈹€鈹€ 涓柇鐢熸垚 鈹€鈹€
  function cancelStream() {
    const last = messages.value[messages.value.length - 1]
    if (last && last.streaming) {
      last.streaming = false
      if (!last.content) {
        last.content = '锛堝凡鍙栨秷锛?
      }
    }
    isStreaming.value = false
    streamingContent.value = ''
  }

  // 鈹€鈹€ 鏂板缓瀵硅瘽 鈹€鈹€
  function newConversation() {
    currentConversationId.value = null
    messages.value = []
    isStreaming.value = false
    streamingContent.value = ''
  }

  // 鈹€鈹€ 鍒犻櫎瀵硅瘽 鈹€鈹€
  async function deleteConversation(id: string) {
    await agentApi.deleteSession(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConversationId.value === id) {
      newConversation()
    }
  }

  // 鈹€鈹€ 閲嶇疆 鈹€鈹€
  function reset() {
    conversations.value = []
    messages.value = []
    currentConversationId.value = null
    isStreaming.value = false
    streamingContent.value = ''
  }

  // 鈹€鈹€ 鍚嶇О纭瀹屾垚 鈹€鈹€
  function markNameConfirmed(messageId: string) {
    const msg = messages.value.find(m => m.id === messageId)
    if (msg && msg.nameConfirm) {
      msg.nameConfirm.confirmed = true
    }
  }

  // 鈹€鈹€ 鍚嶇О纭璺宠繃 鈹€鈹€
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

