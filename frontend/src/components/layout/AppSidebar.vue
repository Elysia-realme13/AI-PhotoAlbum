<template>
  <aside
    class="shrink-0 flex flex-col shadow-sm border-r border-gray-200 dark:border-dark-border bg-white dark:bg-dark-card transition-[width,background-color,border-color] duration-300 overflow-hidden"
    :class="expanded ? 'w-56 sidebar-expanded' : 'w-16 sidebar-collapsed'"
  >
    <!-- Logo区域 -->
    <div class="p-3 border-b border-gray-100 dark:border-dark-border flex items-center justify-between">
      <div class="flex items-center gap-2 overflow-hidden">
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0">
          <el-icon :size="18" color="white"><PictureFilled /></el-icon>
        </div>
        <div class="whitespace-nowrap overflow-hidden menu-title">
          <h1 class="text-gray-800 dark:text-dark-text font-bold text-base">AI 相册</h1>
          <p class="text-gray-400 dark:text-dark-text-secondary text-xs">智能照片管理</p>
        </div>
      </div>
    </div>

    <!-- 主导航菜单 -->
    <el-menu
      :default-active="activeRoute"
      router
      :class="['flex-1 border-r-0 sidebar-menu overflow-y-auto', expanded ? 'sidebar-expanded' : 'sidebar-collapsed']"
      background-color="transparent"
      :text-color="isDark ? '#94a3b8' : '#6b7280'"
      active-text-color="#3b82f6"
    >
      <el-menu-item index="/home" class="sidebar-item">
        <el-tooltip content="首页" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><HomeFilled /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">首页</span></template>
      </el-menu-item>
      <el-menu-item index="/photos" class="sidebar-item">
        <el-tooltip content="照片" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><PictureFilled /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">照片</span></template>
      </el-menu-item>
      <el-menu-item index="/recycle-bin" class="sidebar-item">
        <el-tooltip content="回收站" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><Delete /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">回收站</span></template>
      </el-menu-item>
      <el-menu-item index="/albums" class="sidebar-item">
        <el-tooltip content="相册" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><Folder /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">相册</span></template>
      </el-menu-item>
      <el-menu-item index="/faces" class="sidebar-item">
        <el-tooltip content="人物" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><UserFilled /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">人物</span></template>
      </el-menu-item>
      <el-menu-item index="/map" class="sidebar-item">
        <el-tooltip content="足迹" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><Location /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">足迹</span></template>
      </el-menu-item>
      <el-menu-item index="/search" class="sidebar-item">
        <el-tooltip content="搜索" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><Search /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">搜索</span></template>
      </el-menu-item>
      <el-menu-item index="/agent" class="sidebar-item">
        <el-tooltip content="AI 助手" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><ChatDotRound /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">AI 助手</span></template>
      </el-menu-item>
      <el-menu-item index="/tasks" class="sidebar-item">
        <el-tooltip content="任务中心" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><List /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">任务中心</span></template>
      </el-menu-item>
      <el-menu-item index="/training" class="sidebar-item">
        <el-tooltip content="模型训练" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><TrendCharts /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">模型训练</span></template>
      </el-menu-item>
      <el-menu-item index="/models" class="sidebar-item">
        <el-tooltip content="模型管理" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><Monitor /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">模型管理</span></template>
      </el-menu-item>
      <el-menu-item index="/database" class="sidebar-item">
        <el-tooltip content="数据集管理" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><DataBoard /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">数据集管理</span></template>
      </el-menu-item>
      <el-menu-item index="/settings" class="sidebar-item">
        <el-tooltip content="设置" placement="right" :disabled="expanded" :show-after="1000" :hide-after="0">
          <el-icon><Setting /></el-icon>
        </el-tooltip>
        <template #title><span class="menu-title">设置</span></template>
      </el-menu-item>
    </el-menu>

    <!-- 底部收起按钮 -->
    <div class="border-t border-gray-100 dark:border-dark-border p-2">
      <div
        class="flex items-center justify-center h-9 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors"
        @click="toggle"
      >
        <el-icon :size="18" class="text-gray-500 dark:text-dark-text-secondary">
          <component :is="expanded ? 'Fold' : 'Expand'" />
        </el-icon>
        <span class="ml-2 text-sm text-gray-600 dark:text-dark-text-secondary whitespace-nowrap menu-title">收起</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar-menu {
  --el-menu-bg-color: transparent;
  scrollbar-width: none; /* Firefox */
}

/* 菜单项统一淡入动画（同时、同时长、无错峰）*/
.sidebar-menu :deep(.sidebar-item) {
  animation: sidebar-fade-in 0.8s ease both;
}

@keyframes sidebar-fade-in {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.sidebar-menu :deep(.el-menu) {
  border-right: none;
  min-width: 0 !important;
}

/* 菜单项过渡（padding 保持默认不变，避免跳变）*/
.sidebar-menu :deep(.el-menu-item) {
  transition: background-color 0.3s ease;
}

/* el-tooltip trigger 不影响菜单项布局 */
.sidebar-menu :deep(.el-tooltip__trigger) {
  display: inline-flex;
  align-items: center;
}

/* 菜单文字 — 通过 max-width 控制占位，收起时不占空间 */
:deep(.menu-title) {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  max-width: 200px;
  transition: opacity 0.2s ease, max-width 0.3s ease;
}

.sidebar-collapsed :deep(.menu-title) {
  opacity: 0;
  max-width: 0;
}

/* 自定义滚动条 - 默认隐藏，悬停时显示 */
.sidebar-menu::-webkit-scrollbar {
  width: 6px;
}

.sidebar-menu::-webkit-scrollbar-thumb {
  background-color: transparent;
  border-radius: 3px;
  transition: background-color 0.2s;
}

.sidebar-menu:hover::-webkit-scrollbar-thumb {
  background-color: #c1c1c1;
}

.sidebar-menu::-webkit-scrollbar-track {
  background-color: transparent;
}

/* 收起状态下滚动条向右偏移，避免遮挡图标 */
.sidebar-collapsed::-webkit-scrollbar {
  margin-right: 4px;
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useLayoutStore } from '@/stores/layout'
import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const activeRoute = computed(() => route.path)

const layoutStore = useLayoutStore()
const { sidebarExpanded: expanded } = storeToRefs(layoutStore)
const { toggleSidebar: toggle } = layoutStore

const themeStore = useThemeStore()
const { theme } = storeToRefs(themeStore)
const isDark = computed(() => theme.value === 'dark')
</script>
