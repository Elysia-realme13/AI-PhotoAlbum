import request from '@/utils/request'
import type { Conversation } from '@/types/chat'

interface SessionResponse {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

interface MessageItem {
  id: number
  role: 'user' | 'assistant'
  content: string | object
  tool_calls?: object | null
  created_at: string
}

interface SendMessageResponse {
  reply: string
  results: Array<{ photo_id: string; score: number }>
  total: number
  needs_confirmation: boolean
  pending_candidates: Array<Record<string, unknown>>
  message_id: number
}

export const agentApi = {
  /** 获取对话列表 */
  getConversations() {
    return request.get<SessionResponse[]>('/agent/sessions')
  },

  /** 获取对话消息历史 */
  getMessages(sessionId: string) {
    return request.get<MessageItem[]>(`/agent/sessions/${sessionId}/messages`)
  },

  /** 创建新对话 */
  createSession(title = '新对话') {
    return request.post<SessionResponse>('/agent/sessions', { title })
  },

  /** 发送消息 */
  sendMessage(sessionId: string, message: string, image?: File) {
    const formData = new FormData()
    formData.append('message', message)
    if (image) formData.append('image', image)
    return request.post<SendMessageResponse>(
      `/agent/sessions/${sessionId}/messages`, formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },

  /** 删除对话 */
  deleteSession(sessionId: string) {
    return request.delete(`/agent/sessions/${sessionId}`)
  },

  /** 确认身份名称 */
  confirmName(data: {
    cluster_id: string
    name: string
    session_id: string
    query: string
    aliases?: string[]
  }) {
    return request.post('/faces/identities/name', data)
  },
}
