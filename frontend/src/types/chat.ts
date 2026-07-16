/** 消息角色 */
export type MessageRole = 'user' | 'assistant'

/** 单条聊天消息 */
export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  created_at: string
  streaming?: boolean
  image?: File
  imageUrl?: string
}

/** 对话会话 */
export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

/** 发送消息请求 */
export interface ChatRequest {
  query: string
  conversation_id?: string
}

/** SSE 事件类型 */
export interface ChatEvent {
  type: 'start' | 'chunk' | 'done' | 'error'
  content?: string
  conversation_id?: string
  error?: string
}