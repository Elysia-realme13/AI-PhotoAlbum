<template>
  <router-view v-slot="{ Component }">
    <transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 启动时校验 token 有效性，过期/无效则跳登录
onMounted(async () => {
  if (userStore.token) {
    await userStore.fetchUser() // 失败时 fetchUser 内部已 logout
    if (!userStore.user) router.push('/login')
  }
})
</script>
