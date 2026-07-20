<template>
  <div class="min-h-screen bg-white dark:bg-dark-bg">
    <!-- 顶部导航栏 -->
    <header class="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-dark-bg/80 backdrop-blur-md border-b border-gray-100 dark:border-dark-border">
      <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
            <el-icon :size="20" color="white"><PictureFilled /></el-icon>
          </div>
          <span class="text-lg font-bold text-gray-800 dark:text-dark-text">AI 智能相册</span>
        </router-link>

        <!-- 右侧操作 -->
        <div class="flex items-center gap-4">
          <el-button
            type="primary"
            size="large"
            round
            @click="$router.push('/login')"
          >
            登录
          </el-button>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main>
      <!-- Hero 区域 -->
      <section class="relative pt-32 pb-24 px-6 overflow-hidden">
        <!-- 背景装饰 -->
        <div class="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-dark-bg dark:via-dark-card dark:to-dark-bg" />
        <div class="absolute top-20 left-1/4 w-72 h-72 bg-blue-400/10 rounded-full blur-3xl" />
        <div class="absolute bottom-10 right-1/4 w-96 h-96 bg-indigo-400/10 rounded-full blur-3xl" />

        <div class="relative max-w-4xl mx-auto text-center">
          <div class="inline-flex items-center gap-2 px-4 py-1.5 mb-6 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-sm font-medium">
            <el-icon><StarFilled /></el-icon>
            AI 驱动的智能照片管理
          </div>

          <h1 class="text-5xl md:text-6xl font-extrabold text-gray-900 dark:text-dark-text leading-tight mb-6">
            让每一张照片<br />
            <span class="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">都有故事可讲</span>
          </h1>

          <p class="text-lg md:text-xl text-gray-500 dark:text-dark-text-secondary max-w-2xl mx-auto mb-10">
            AI 智能相册帮你自动整理、智能分类、快速搜索，
            让人脸识别、场景理解和自然语言搜索触手可及。
          </p>

          <div class="flex items-center justify-center gap-4">
            <el-button type="primary" size="large" round class="!px-8 !py-3 !text-base" @click="$router.push('/login')">
              立即开始
            </el-button>
            <el-button size="large" round class="!px-8 !py-3 !text-base" @click="scrollToFeatures">
              了解更多
            </el-button>
          </div>
        </div>
      </section>

      <!-- 功能亮点 -->
      <section id="features" ref="featuresRef" class="max-w-7xl mx-auto px-6 py-24">
        <div class="text-center mb-16">
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-dark-text mb-4">
            核心功能
          </h2>
          <p class="text-gray-500 dark:text-dark-text-secondary text-lg max-w-xl mx-auto">
            全方位的 AI 能力，让你的照片管理变得更简单
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <!-- 功能卡片 -->
          <div
            v-for="feature in features"
            :key="feature.title"
            class="group relative p-8 rounded-2xl bg-gray-50 dark:bg-dark-card border border-gray-100 dark:border-dark-border hover:border-blue-200 dark:hover:border-blue-800 hover:shadow-lg transition-all duration-300"
          >
            <div class="w-12 h-12 rounded-xl mb-5 flex items-center justify-center text-white bg-gradient-to-br" :class="feature.gradient">
              <el-icon :size="24"><component :is="feature.icon" /></el-icon>
            </div>
            <h3 class="text-lg font-semibold text-gray-800 dark:text-dark-text mb-2">{{ feature.title }}</h3>
            <p class="text-gray-500 dark:text-dark-text-secondary text-sm leading-relaxed">{{ feature.desc }}</p>
          </div>
        </div>
      </section>

      <!-- 场景展示 -->
      <section class="max-w-7xl mx-auto px-6 py-24">
        <div class="text-center mb-16">
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-dark-text mb-4">
            使用场景
          </h2>
          <p class="text-gray-500 dark:text-dark-text-secondary text-lg">
            覆盖照片管理的每一个环节
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div
            v-for="(scene, idx) in scenes"
            :key="idx"
            class="relative overflow-hidden rounded-2xl bg-gradient-to-br p-8 text-white"
            :class="scene.gradient"
          >
            <el-icon :size="36" class="mb-4 opacity-90"><component :is="scene.icon" /></el-icon>
            <h3 class="text-xl font-bold mb-2">{{ scene.title }}</h3>
            <p class="text-white/80 text-sm leading-relaxed">{{ scene.desc }}</p>
          </div>
        </div>
      </section>

      <!-- 底部 CTA -->
      <section class="max-w-4xl mx-auto px-6 py-24 text-center">
        <div class="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-3xl p-12 md:p-16">
          <h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
            准备好开始了吗？
          </h2>
          <p class="text-blue-100 text-lg mb-8 max-w-lg mx-auto">
            免费注册，体验 AI 驱动的智能相册管理
          </p>
          <el-button
            size="large"
            round
            class="!bg-white !text-blue-600 !border-white !px-10 !py-3 !text-base hover:!bg-blue-50"
            @click="$router.push('/login')"
          >
            免费开始使用
          </el-button>
        </div>
      </section>
    </main>

    <!-- 底部 -->
    <footer class="border-t border-gray-100 dark:border-dark-border py-8">
      <div class="max-w-7xl mx-auto px-6 text-center text-sm text-gray-400 dark:text-dark-text-secondary">
        © {{ new Date().getFullYear() }} AI 智能相册 · 让每一张照片都有故事可讲
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { PictureFilled, StarFilled, Camera, Search, ChatDotRound, VideoPlay, DataBoard, TrendCharts, UserFilled, Folder, Location } from '@element-plus/icons-vue'

const featuresRef = ref<HTMLElement | null>(null)

function scrollToFeatures() {
  featuresRef.value?.scrollIntoView({ behavior: 'smooth' })
}

const features = [
  {
    icon: Search,
    title: '智能搜索',
    desc: '支持自然语言搜索照片，输入「去年夏天在海边拍的照片」即可精准定位，也支持以图搜图。',
    gradient: 'from-blue-500 to-blue-600',
  },
  {
    icon: UserFilled,
    title: '人脸识别',
    desc: '自动检测并聚类人脸，一键命名后即可按人物浏览照片，轻松找到家人朋友的所有瞬间。',
    gradient: 'from-indigo-500 to-indigo-600',
  },
  {
    icon: Folder,
    title: '智能相册',
    desc: '根据时间、地点、场景、人物自动生成动态相册，无需手动整理，照片井井有条。',
    gradient: 'from-purple-500 to-purple-600',
  },
  {
    icon: Location,
    title: '足迹地图',
    desc: '基于照片 GPS 信息自动生成旅行足迹地图，可视化展示你去过的每一个地方。',
    gradient: 'from-emerald-500 to-emerald-600',
  },
  {
    icon: ChatDotRound,
    title: 'AI 对话助手',
    desc: '用对话的方式与照片库交互，AI 理解你的意图并帮你查找、整理、管理照片。',
    gradient: 'from-orange-500 to-orange-600',
  },
  {
    icon: TrendCharts,
    title: '模型训练',
    desc: '支持自定义人脸识别模型训练，让你的 AI 越来越懂你，识别准确率持续提升。',
    gradient: 'from-pink-500 to-pink-600',
  },
]

const scenes = [
  {
    icon: Camera,
    title: '自动导入',
    desc: '拖拽或批量上传照片，自动提取 EXIF 信息、生成缩略图，智能标签即刻就位。',
    gradient: 'from-blue-600 to-cyan-600',
  },
  {
    icon: DataBoard,
    title: '数据看板',
    desc: '照片数量、存储空间、任务进度一目了然，数据集管理让模型训练更高效。',
    gradient: 'from-indigo-600 to-purple-600',
  },
  {
    icon: VideoPlay,
    title: '即时预览',
    desc: '支持网格视图和时间线视图，点击即可全屏预览，照片浏览体验丝滑流畅。',
    gradient: 'from-purple-600 to-pink-600',
  },
]
</script>
