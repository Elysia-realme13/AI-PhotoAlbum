<template>
  <aside class="w-56 bg-gradient-to-b from-slate-900 to-slate-800 shrink-0 flex flex-col shadow-xl">
    <!-- Logo区域 -->
    <div class="p-4 border-b border-slate-700 sidebar-logo">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
          <el-icon :size="20" color="white"><PictureFilled /></el-icon>
        </div>
        <div>
          <h1 class="text-white font-bold text-lg">AI 相册</h1>
          <p class="text-slate-400 text-xs">智能照片管理</p>
        </div>
      </div>
    </div>

    <!-- 主导航菜单 -->
    <el-menu
      :default-active="activeRoute"
      router
      class="flex-1 border-r-0 sidebar-menu"
      background-color="transparent"
      text-color="#94a3b8"
      active-text-color="#ffffff"
    >
      <el-menu-item index="/home" class="sidebar-item">
        <el-icon><HomeFilled /></el-icon>
        <span>首页</span>
      </el-menu-item>
      <el-menu-item index="/photos" class="sidebar-item">
        <el-icon><PictureFilled /></el-icon>
        <span>照片</span>
      </el-menu-item>
      <el-menu-item index="/recycle-bin" class="sidebar-item">
        <el-icon><Delete /></el-icon>
        <span>回收站</span>
      </el-menu-item>
      <el-menu-item index="/albums" class="sidebar-item">
        <el-icon><Folder /></el-icon>
        <span>相册</span>
      </el-menu-item>
      <el-menu-item index="/faces" class="sidebar-item">
        <el-icon><UserFilled /></el-icon>
        <span>人物</span>
      </el-menu-item>
      <el-menu-item index="/map" class="sidebar-item">
        <el-icon><Location /></el-icon>
        <span>足迹</span>
      </el-menu-item>
      <el-menu-item index="/search" class="sidebar-item">
        <el-icon><Search /></el-icon>
        <span>搜索</span>
      </el-menu-item>
      <el-menu-item index="/agent" class="sidebar-item">
        <el-icon><ChatDotRound /></el-icon>
        <span>AI 助手</span>
      </el-menu-item>
    </el-menu>

    <!-- 底部设置菜单 -->
    <div class="border-t border-slate-700 p-0">
      <el-menu
        background-color="transparent"
        text-color="#94a3b8"
        active-text-color="#ffffff"
        router
        class="border-r-0 sidebar-menu"
      >
        <el-menu-item index="/settings" class="sidebar-item">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeRoute = computed(() => route.path)
</script>
