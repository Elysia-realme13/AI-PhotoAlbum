import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import { useChatStore } from '@/stores/chat'

// 上次登录用户（用于登录页头像展示，登出后仍保留）
const LAST_USER_KEY = 'lastLoginUser'
// 本地登录过的所有用户（按 username 去重，末尾为最近登录），用于登录页按输入匹配头像
const KNOWN_USERS_KEY = 'knownLoginUsers'

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
    // 记住用于登录页展示（登出后仍保留）
    localStorage.setItem(
      LAST_USER_KEY,
      JSON.stringify({
        username: userInfo.username,
        nickname: userInfo.nickname,
        avatar_url: userInfo.avatar_url,
      }),
    )
    // 追加到本地已知用户列表（按 username 去重，末尾为最近登录）
    try {
      const rawList = localStorage.getItem(KNOWN_USERS_KEY)
      const list: KnownUser[] = rawList ? JSON.parse(rawList) : []
      const filtered = list.filter((u) => u.username !== userInfo.username)
      filtered.push({
        username: userInfo.username,
        email: userInfo.email,
        nickname: userInfo.nickname,
        avatar_url: userInfo.avatar_url,
      })
      localStorage.setItem(KNOWN_USERS_KEY, JSON.stringify(filtered))
    } catch {
      // ignore
    }
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

export interface LastLoginUser {
  username: string
  nickname?: string
  avatar_url?: string
}

/** 读取上次登录用户信息（用于登录页头像展示，登出后仍保留） */
export function getLastLoginUser(): LastLoginUser | null {
  const raw = localStorage.getItem(LAST_USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as LastLoginUser
  } catch {
    return null
  }
}

export interface KnownUser {
  username: string
  email?: string
  nickname?: string
  avatar_url?: string
}

/** 读取本地登录过的所有用户（按 username 去重，末尾为最近登录） */
export function getKnownUsers(): KnownUser[] {
  const raw = localStorage.getItem(KNOWN_USERS_KEY)
  if (!raw) return []
  try {
    const list = JSON.parse(raw)
    return Array.isArray(list) ? (list as KnownUser[]) : []
  } catch {
    return []
  }
}
