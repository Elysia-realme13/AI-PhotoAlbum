<template>
  <header class="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
    <div class="flex items-center gap-3">
      <el-icon :size="22" color="#409EFF"><PictureFilled /></el-icon>
      <h1 class="text-lg font-semibold text-gray-800">AI 智能相册</h1>
    </div>

    <div class="flex items-center gap-4">
      <el-dropdown trigger="click">
        <div class="flex items-center gap-2 cursor-pointer">
          <el-avatar :size="32" :src="user?.avatar_url">
            {{ user?.nickname?.charAt(0) || 'U' }}
          </el-avatar>
          <span class="text-sm text-gray-600">{{ user?.nickname || user?.username }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/settings')">
              <el-icon><Setting /></el-icon> 设置
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">
              <el-icon><SwitchButton /></el-icon> 退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const { user } = storeToRefs(userStore)

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>
