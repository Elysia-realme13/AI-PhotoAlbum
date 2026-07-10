<template>
  <aside class="w-56 bg-white border-r border-gray-200 shrink-0 flex flex-col">
    <el-menu
      :default-active="activeRoute"
      router
      class="flex-1 border-r-0"
      background-color="#ffffff"
      text-color="#606266"
      active-text-color="#409EFF"
    >
      <el-menu-item index="/home">
        <el-icon><HomeFilled /></el-icon>
        <span>首页</span>
      </el-menu-item>
      <el-menu-item index="/photos">
        <el-icon><PictureFilled /></el-icon>
        <span>照片</span>
      </el-menu-item>
      <el-menu-item index="/albums">
        <el-icon><Folder /></el-icon>
        <span>相册</span>
      </el-menu-item>
      <el-menu-item index="/faces">
        <el-icon><UserFilled /></el-icon>
        <span>人物</span>
      </el-menu-item>
      <el-menu-item index="/map">
        <el-icon><Location /></el-icon>
        <span>足迹</span>
      </el-menu-item>
      <el-menu-item index="/search">
        <el-icon><Search /></el-icon>
        <span>搜索</span>
      </el-menu-item>
      <el-menu-item index="/agent">
        <el-icon><ChatDotRound /></el-icon>
        <span>AI 助手</span>
      </el-menu-item>
    </el-menu>

    <div class="border-t border-gray-200 p-0">
      <el-menu
        background-color="#ffffff"
        text-color="#909399"
        active-text-color="#409EFF"
        router
        class="border-r-0"
      >
        <el-menu-item index="/settings">
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
