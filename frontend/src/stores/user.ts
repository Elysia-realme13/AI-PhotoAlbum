import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import { useChatStore } from '@/stores/chat'

export interface UserInfo {
  id: string
  username: string
  email: string
  nickname?: string
  avatar_url?: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  function setAuth(authToken: string, userInfo: UserInfo) {
    token.value = authToken
    user.value = userInfo
    localStorage.setItem('token', authToken)
    localStorage.setItem('user', JSON.stringify(userInfo))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    useChatStore().reset()   // 清理聊天数据，避免跨用户串号
  }

  async function fetchUser() {
    try {
      const res = await authApi.getMe()
      user.value = res.data
    } catch {
      logout()
    }
  }

  // 从缓存恢复
  const cachedUser = localStorage.getItem('user')
  if (cachedUser) {
    try {
      user.value = JSON.parse(cachedUser)
    } catch {
      // ignore
    }
  }

  return { user, token, setAuth, logout, fetchUser }
})
