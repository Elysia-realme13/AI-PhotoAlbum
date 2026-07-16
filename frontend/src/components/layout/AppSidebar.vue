<template>
  <aside
    class="shrink-0 flex flex-col shadow-sm border-r border-gray-200 dark:border-dark-border bg-white dark:bg-dark-card transition-all duration-300"
    :class="expanded ? 'w-56' : 'w-16'"
  >
    <!-- Logo区域 -->
    <div class="p-3 border-b border-gray-100 dark:border-dark-border flex items-center justify-between">
      <div class="flex items-center gap-2 overflow-hidden">
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0">
          <el-icon :size="18" color="white"><PictureFilled /></el-icon>
        </div>
        <div v-show="expanded" class="whitespace-nowrap">
          <h1 class="text-gray-800 dark:text-dark-text font-bold text-base">AI 相册</h1>
          <p class="text-gray-400 dark:text-dark-text-secondary text-xs">智能照片管理</p>
        </div>
      </div>
    </div>

    <!-- 主导航菜单 -->
    <el-menu
      :default-active="activeRoute"
      :collapse="!expanded"
      router
      popper-class="sidebar-tooltip"
      :class="['flex-1 border-r-0 sidebar-menu overflow-y-auto', expanded ? 'sidebar-expanded' : 'sidebar-collapsed']"
      background-color="transparent"
      :text-color="isDark ? '#94a3b8' : '#6b7280'"
      active-text-color="#3b82f6"
    >
      <el-menu-item index="/home" class="sidebar-item">
        <el-icon><HomeFilled /></el-icon>
        <template #title>首页</template>
      </el-menu-item>
      <el-menu-item index="/photos" class="sidebar-item">
        <el-icon><PictureFilled /></el-icon>
        <template #title>照片</template>
      </el-menu-item>
      <el-menu-item index="/recycle-bin" class="sidebar-item">
        <el-icon><Delete /></el-icon>
        <template #title>回收站</template>
      </el-menu-item>
      <el-menu-item index="/albums" class="sidebar-item">
        <el-icon><Folder /></el-icon>
        <template #title>相册</template>
      </el-menu-item>
      <el-menu-item index="/faces" class="sidebar-item">
        <el-icon><UserFilled /></el-icon>
        <template #title>人物</template>
      </el-menu-item>
      <el-menu-item index="/map" class="sidebar-item">
        <el-icon><Location /></el-icon>
        <template #title>足迹</template>
      </el-menu-item>
      <el-menu-item index="/search" class="sidebar-item">
        <el-icon><Search /></el-icon>
        <template #title>搜索</template>
      </el-menu-item>
      <el-menu-item index="/agent" class="sidebar-item">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>AI 助手</template>
      </el-menu-item>
      <el-menu-item index="/training" class="sidebar-item">
        <el-icon><TrendCharts /></el-icon>
        <template #title>模型训练</template>
      </el-menu-item>
      <el-menu-item index="/models" class="sidebar-item">
        <el-icon><Monitor /></el-icon>
        <template #title>模型管理</template>
      </el-menu-item>
      <el-menu-item index="/database" class="sidebar-item">
        <el-icon><DataBoard /></el-icon>
        <template #title>数据集管理</template>
      </el-menu-item>
      <el-menu-item index="/settings" class="sidebar-item">
        <el-icon><Setting /></el-icon>
        <template #title>设置</template>
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
        <span v-show="expanded" class="ml-2 text-sm text-gray-600 dark:text-dark-text-secondary">收起</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar-menu {
  --el-menu-bg-color: transparent;
  scrollbar-width: none; /* Firefox */
}

.sidebar-menu :deep(.el-menu) {
  border-right: none;
}

/* 收起状态下覆盖 Element Plus 默认宽度 */
:deep(.el-menu--collapse) {
  width: 100%;
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
