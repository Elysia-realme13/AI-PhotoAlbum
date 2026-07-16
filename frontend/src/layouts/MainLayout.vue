<template>
  <div class="h-screen flex flex-col">
    <!-- 顶部导航 -->
    <app-header />

    <div class="flex flex-1 overflow-hidden">
      <!-- 侧边栏 -->
      <app-sidebar />

      <!-- 主内容区 -->
      <main class="flex-1 overflow-auto bg-gray-50 dark:bg-dark-bg p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
</script>
