<template>
  <div class="min-h-screen bg-white dark:bg-dark-bg">
    <!-- 顶部导航栏 -->
    <header
      ref="navbarRef"
      class="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      :class="scrolled ? 'bg-white/95 dark:bg-dark-bg/95 shadow-sm backdrop-blur-md border-b border-gray-100 dark:border-dark-border' : 'bg-white/60 dark:bg-dark-bg/60 backdrop-blur-md border-b border-transparent'"
    >
      <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-3 group">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <el-icon :size="20" color="white"><PictureFilled /></el-icon>
          </div>
          <span class="text-lg font-bold text-gray-800 dark:text-dark-text">AI 智能相册</span>
        </router-link>

        <div class="flex items-center gap-4">
          <el-button
            type="primary"
            size="large"
            round
            class="!shadow-lg !shadow-blue-500/25 hover:!shadow-blue-500/40 !transition-shadow"
            @click="$router.push('/login')"
          >
            登录
          </el-button>
        </div>
      </div>
    </header>

    <main>
      <!-- ═══════════ Hero 区域 ═══════════ -->
      <section class="relative pt-32 pb-28 px-6 overflow-hidden">
        <!-- 动态背景 -->
        <div class="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-dark-bg dark:via-dark-card dark:to-dark-bg" />
        <!-- 浮动光斑 -->
        <div class="absolute top-20 left-1/4 w-72 h-72 bg-blue-400/10 rounded-full blur-3xl floating-slow" />
        <div class="absolute bottom-10 right-1/4 w-96 h-96 bg-indigo-400/10 rounded-full blur-3xl floating-medium" />
        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-400/5 rounded-full blur-3xl floating-fast" />
        <!-- 装饰性浮动图标 -->
        <div class="absolute top-24 left-[15%] opacity-10 dark:opacity-5 floating-icon" style="animation-delay: 0s">
          <el-icon :size="28" color="#3b82f6"><PictureFilled /></el-icon>
        </div>
        <div class="absolute top-40 right-[20%] opacity-10 dark:opacity-5 floating-icon" style="animation-delay: 1.5s">
          <el-icon :size="24" color="#6366f1"><Camera /></el-icon>
        </div>
        <div class="absolute bottom-32 left-[25%] opacity-10 dark:opacity-5 floating-icon" style="animation-delay: 3s">
          <el-icon :size="22" color="#8b5cf6"><StarFilled /></el-icon>
        </div>
        <div class="absolute top-60 right-[12%] opacity-10 dark:opacity-5 floating-icon" style="animation-delay: 4.5s">
          <el-icon :size="32" color="#ec4899"><VideoPlay /></el-icon>
        </div>

        <!-- Hero 内容 -->
        <div class="relative max-w-4xl mx-auto text-center">
          <div
            ref="heroBadgeRef"
            class="reveal-up inline-flex items-center gap-2 px-4 py-1.5 mb-6 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-sm font-medium border border-blue-100 dark:border-blue-800/30"
          >
            <el-icon class="pulse-dot"><StarFilled /></el-icon>
            AI 驱动的智能照片管理
          </div>

          <h1 ref="heroTitleRef" class="reveal-up-delayed text-5xl md:text-6xl font-extrabold text-gray-900 dark:text-dark-text leading-tight mb-6">
            让每一张照片<br />
            <span class="gradient-text bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient">
              都有故事可讲
            </span>
          </h1>

          <p ref="heroDescRef" class="reveal-up-more text-lg md:text-xl text-gray-500 dark:text-dark-text-secondary max-w-2xl mx-auto mb-10">
            AI 智能相册帮你自动整理、智能分类、快速搜索，
            让人脸识别、场景理解和自然语言搜索触手可及。
          </p>

          <div ref="heroBtnsRef" class="reveal-up-most flex items-center justify-center gap-4">
            <el-button type="primary" size="large" round class="!px-8 !py-3 !text-base btn-pulse" @click="$router.push('/login')">
              立即开始
            </el-button>
            <el-button size="large" round class="!px-8 !py-3 !text-base" @click="scrollToFeatures">
              了解更多
            </el-button>
          </div>
        </div>

        <!-- 向下滚动提示 -->
        <button
          class="absolute bottom-6 left-1/2 -translate-x-1/2 animate-bounce opacity-40 hover:opacity-70 transition-opacity cursor-pointer border-none bg-transparent p-2"
          @click="scrollToFeatures"
          aria-label="向下滚动"
        >
          <el-icon :size="20"><ArrowDown /></el-icon>
        </button>
      </section>

      <!-- ═══════════ 数据统计 ═══════════ -->
      <section ref="statsRef" class="max-w-5xl mx-auto px-6 py-16">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div
            v-for="(stat, i) in stats"
            :key="i"
            class="text-center stat-item"
            :style="{ transitionDelay: `${i * 0.1}s` }"
          >
            <div class="text-3xl md:text-4xl font-extrabold text-gray-900 dark:text-dark-text mb-1">
              <span ref="countRefs">{{ animatedStats[i]?.display ?? 0 }}</span>{{ stat.suffix }}
            </div>
            <div class="text-sm text-gray-500 dark:text-dark-text-secondary">{{ stat.label }}</div>
          </div>
        </div>
      </section>

      <!-- ═══════════ 功能亮点 ═══════════ -->
      <section id="features" ref="featuresRef" class="max-w-7xl mx-auto px-6 py-24">
        <div ref="featuresHeaderRef" class="reveal-up text-center mb-16">
          <div class="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-xs font-medium">
            核心功能
          </div>
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-dark-text mb-4">
            全方位的 AI 能力
          </h2>
          <p class="text-gray-500 dark:text-dark-text-secondary text-lg max-w-xl mx-auto">
            让你的照片管理变得更简单、更智能
          </p>
        </div>

        <!-- 第一行：2 个 -->
        <div class="flex flex-wrap justify-center gap-6 mb-6">
          <div
            v-for="(feature, i) in features.slice(0, 2)"
            :key="feature.title"
            :style="{ transitionDelay: `${0.05 + i * 0.07}s` }"
            class="feature-card group relative p-8 rounded-2xl bg-gray-50 dark:bg-dark-card border border-gray-100 dark:border-dark-border hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-xl hover:-translate-y-1 transition-all duration-500 overflow-hidden w-full md:w-[calc(50%-12px)]"
          >
            <!-- 卡片背景光效 -->
            <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-blue-50/50 via-transparent to-transparent dark:from-blue-900/10" />
            <div class="relative z-10">
              <div class="w-12 h-12 rounded-xl mb-5 flex items-center justify-center text-white bg-gradient-to-br group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300" :class="feature.gradient">
                <el-icon :size="24"><component :is="feature.icon" /></el-icon>
              </div>
              <h3 class="text-lg font-semibold text-gray-800 dark:text-dark-text mb-2">{{ feature.title }}</h3>
              <p class="text-gray-500 dark:text-dark-text-secondary text-sm leading-relaxed">{{ feature.desc }}</p>
            </div>
          </div>
        </div>
        <!-- 第二行：3 个 -->
        <div class="flex flex-wrap justify-center gap-6">
          <div
            v-for="(feature, i) in features.slice(2)"
            :key="feature.title"
            :style="{ transitionDelay: `${0.05 + (i + 2) * 0.07}s` }"
            class="feature-card group relative p-8 rounded-2xl bg-gray-50 dark:bg-dark-card border border-gray-100 dark:border-dark-border hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-xl hover:-translate-y-1 transition-all duration-500 overflow-hidden w-full md:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)]"
          >
            <!-- 卡片背景光效 -->
            <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-blue-50/50 via-transparent to-transparent dark:from-blue-900/10" />
            <div class="relative z-10">
              <div class="w-12 h-12 rounded-xl mb-5 flex items-center justify-center text-white bg-gradient-to-br group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300" :class="feature.gradient">
                <el-icon :size="24"><component :is="feature.icon" /></el-icon>
              </div>
              <h3 class="text-lg font-semibold text-gray-800 dark:text-dark-text mb-2">{{ feature.title }}</h3>
              <p class="text-gray-500 dark:text-dark-text-secondary text-sm leading-relaxed">{{ feature.desc }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════ 操作流程 ═══════════ -->
      <section ref="stepsRef" class="max-w-5xl mx-auto px-6 py-24">
        <div ref="stepsHeaderRef" class="reveal-up text-center mb-16">
          <div class="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-xs font-medium">
            三步开始
          </div>
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-dark-text mb-4">
            简单三步，开启智能相册
          </h2>
          <p class="text-gray-500 dark:text-dark-text-secondary text-lg">
            无需复杂配置，几分钟即可上手
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          <!-- 连接线（桌面端） -->
          <div class="steps-line hidden md:block absolute top-12 left-[18%] right-[18%] h-0.5 bg-gradient-to-r from-blue-300 via-indigo-300 to-purple-300 dark:from-blue-800 dark:via-indigo-800 dark:to-purple-800" />

          <div
            v-for="(step, i) in steps"
            :key="i"
            :style="{ transitionDelay: `${0.05 + i * 0.1}s` }"
            class="step-card relative text-center"
          >
            <div class="relative inline-flex mb-6">
              <div class="w-24 h-24 rounded-2xl flex items-center justify-center text-white bg-gradient-to-br shadow-lg" :class="step.gradient">
                <el-icon :size="36"><component :is="step.icon" /></el-icon>
              </div>
              <div class="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-white dark:bg-dark-card border-2 border-gray-200 dark:border-dark-border flex items-center justify-center text-sm font-bold text-gray-600 dark:text-dark-text-secondary">
                {{ i + 1 }}
              </div>
            </div>
            <h3 class="text-xl font-bold text-gray-800 dark:text-dark-text mb-2">{{ step.title }}</h3>
            <p class="text-gray-500 dark:text-dark-text-secondary text-sm leading-relaxed">{{ step.desc }}</p>
          </div>
        </div>
      </section>

      <!-- ═══════════ 技术栈 ═══════════ -->
      <section ref="techRef" class="max-w-5xl mx-auto px-6 py-24">
        <div ref="techHeaderRef" class="reveal-up text-center mb-16">
          <div class="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 text-xs font-medium">
            技术架构
          </div>
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-dark-text mb-4">
            前沿技术栈驱动
          </h2>
          <p class="text-gray-500 dark:text-dark-text-secondary text-lg">
            整合业界领先的 AI 模型与现代化开发框架
          </p>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div
            v-for="(tech, i) in techs"
            :key="tech.name"
            :style="{ transitionDelay: `${0.02 + i * 0.03}s` }"
            class="tech-item flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-50 dark:bg-dark-card border border-gray-100 dark:border-dark-border hover:border-blue-200 dark:hover:border-blue-800 hover:shadow-md hover:-translate-y-1 transition-all duration-300"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-white text-xs font-bold" :class="tech.color">
              {{ tech.abbr }}
            </div>
            <span class="text-xs text-gray-600 dark:text-dark-text-secondary font-medium">{{ tech.name }}</span>
          </div>
        </div>
      </section>

      <!-- ═══════════ 使用场景 ═══════════ -->
      <section ref="scenesRef" class="max-w-7xl mx-auto px-6 py-24">
        <div ref="scenesHeaderRef" class="reveal-up text-center mb-16">
          <div class="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 text-xs font-medium">
            使用场景
          </div>
          <h2 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-dark-text mb-4">
            覆盖每一个环节
          </h2>
          <p class="text-gray-500 dark:text-dark-text-secondary text-lg">
            从导入到浏览，全流程 AI 加持
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div
            v-for="(scene, idx) in scenes"
            :key="idx"
            :style="{ transitionDelay: `${0.05 + idx * 0.1}s` }"
            class="scene-card relative overflow-hidden rounded-2xl bg-gradient-to-br p-8 text-white group cursor-default"
            :class="scene.gradient"
          >
            <div class="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 group-hover:scale-150 transition-transform duration-700" />
            <el-icon :size="36" class="mb-4 opacity-90 group-hover:scale-110 transition-transform duration-300"><component :is="scene.icon" /></el-icon>
            <h3 class="text-xl font-bold mb-2">{{ scene.title }}</h3>
            <p class="text-white/80 text-sm leading-relaxed">{{ scene.desc }}</p>
          </div>
        </div>
      </section>

      <!-- ═══════════ 底部 CTA ═══════════ -->
      <section ref="ctaRef" class="max-w-4xl mx-auto px-6 py-24 text-center">
        <div class="reveal-up bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-3xl p-12 md:p-16 shadow-2xl shadow-blue-500/20 relative overflow-hidden">
          <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
          <div class="relative z-10">
            <h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
              准备好开始了吗？
            </h2>
            <p class="text-blue-100 text-lg mb-8 max-w-lg mx-auto">
              免费注册，体验 AI 驱动的智能相册管理
            </p>
            <el-button
              size="large"
              round
              class="!bg-white !text-blue-600 !border-white !px-10 !py-3 !text-base hover:!bg-blue-50 !shadow-lg !transition-all hover:!scale-105"
              @click="$router.push('/login')"
            >
              免费开始使用
            </el-button>
          </div>
        </div>
      </section>
    </main>

    <!-- 底部 -->
    <footer class="border-t border-gray-100 dark:border-dark-border py-8">
      <div class="max-w-7xl mx-auto px-6 text-center text-sm text-gray-400 dark:text-dark-text-secondary space-y-2">
        <p class="text-xs text-gray-300 dark:text-gray-600">
          ※ 本页面展示的数据（用户数、照片量、准确率等）均为示例数据，仅用于产品功能介绍，不代表真实运营数据。
        </p>
        © {{ new Date().getFullYear() }} AI 智能相册 · 让每一张照片都有故事可讲
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import {
  PictureFilled, StarFilled, Camera, ChatDotRound,
  VideoPlay, DataBoard, TrendCharts, UserFilled, Folder, Location,
  ArrowDown, Upload, Setting, Promotion,
} from '@element-plus/icons-vue'

// ── 滚动状态 ─────────────────────────
const navbarRef = ref<HTMLElement | null>(null)
const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 50
}

// ── 滚动触发动画 ─────────────────────
function useRevealOnScroll() {
  const observer = ref<IntersectionObserver | null>(null)

  function observe(el: Element | null | undefined) {
    if (!el || !observer.value) return
    observer.value.observe(el)
  }

  onMounted(() => {
    observer.value = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible')
          }
        })
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    )

    // 观察所有带 reveal 类名的元素
    document.querySelectorAll('.reveal-up, .reveal-up-delayed, .reveal-up-more, .reveal-up-most, .feature-card, .step-card, .tech-item, .scene-card, .stat-item, .steps-line').forEach(el => observe(el))
  })

  onUnmounted(() => {
    observer.value?.disconnect()
  })
}

// ── refs ─────────────────────────────
const featuresRef = ref<HTMLElement | null>(null)
const countRefs = ref<HTMLElement[]>([])

function scrollToFeatures() {
  featuresRef.value?.scrollIntoView({ behavior: 'smooth' })
}

// ── 计数器动画 ───────────────────────
const animatedStats = reactive<{ display: number }[]>([])

const stats = [
  { target: 10000, suffix: '+', label: '照片智能管理', display: 0 },
  { target: 99.9, suffix: '%', label: '人脸识别准确率', display: 0 },
  { target: 12, suffix: '', label: 'AI 核心能力', display: 0 },
  { target: 1000, suffix: '+', label: '满意用户', display: 0 },
]

stats.forEach((s, i) => {
  animatedStats[i] = reactive({ display: 0 })
})

function animateCount(el: Element, target: number, displayObj: { display: number }, decimals: number) {
  const duration = 2000
  const start = performance.now()

  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    // ease-out
    const eased = 1 - Math.pow(1 - progress, 3)
    const current = target * eased

    displayObj.display = decimals > 0 ? Math.round(current * Math.pow(10, decimals)) / Math.pow(10, decimals) : Math.round(current)

    if (progress < 1) {
      requestAnimationFrame(tick)
    }
  }

  requestAnimationFrame(tick)
}

// ── Intersection Observer for counters ──
let statsObserver: IntersectionObserver | null = null

// ── 初始化滚动动画观察器（必须在 setup 顶层调用）───
useRevealOnScroll()

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })

  // 统计数据计数器
  const statsEl = document.querySelector('.stat-item')?.parentElement
  if (statsEl) {
    statsObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          stats.forEach((s, i) => {
            const el = document.querySelectorAll('.stat-item')[i]
            if (el) animateCount(el, stats[i].target, animatedStats[i], stats[i].target % 1 !== 0 ? 1 : 0)
          })
          statsObserver?.disconnect()
        }
      },
      { threshold: 0.3 }
    )
    statsObserver.observe(statsEl)
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  statsObserver?.disconnect()
})

// ── 功能列表 ─────────────────────────
const features = [
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

// ── 操作步骤 ─────────────────────────
const steps = [
  {
    icon: Upload,
    title: '上传照片',
    desc: '拖拽或批量上传，支持 JPEG、PNG、HEIC 等主流格式，自动去重。',
    gradient: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Setting,
    title: 'AI 自动处理',
    desc: '自动提取 EXIF、检测人脸、生成标签、向量化，一切在后台静默完成。',
    gradient: 'from-indigo-500 to-purple-500',
  },
  {
    icon: Promotion,
    title: '随心浏览',
    desc: '按人物、地点、时间、场景随心浏览，享受智能相册的每一刻。',
    gradient: 'from-purple-500 to-pink-500',
  },
]

// ── 技术栈 ───────────────────────────
const techs = [
  { name: 'FastAPI', abbr: 'FA', color: 'bg-teal-500' },
  { name: 'Vue 3', abbr: 'V3', color: 'bg-emerald-500' },
  { name: 'PostgreSQL', abbr: 'PG', color: 'bg-blue-500' },
  { name: 'pgvector', abbr: 'PV', color: 'bg-indigo-500' },
  { name: 'LangChain', abbr: 'LC', color: 'bg-green-500' },
  { name: 'InsightFace', abbr: 'IF', color: 'bg-orange-500' },
  { name: 'CLIP', abbr: 'CL', color: 'bg-purple-500' },
  { name: 'YOLO11', abbr: 'YO', color: 'bg-red-500' },
  { name: 'ONNX', abbr: 'ON', color: 'bg-cyan-500' },
  { name: 'Docker', abbr: 'DK', color: 'bg-sky-500' },
  { name: 'Element Plus', abbr: 'EP', color: 'bg-blue-400' },
  { name: 'TailwindCSS', abbr: 'TW', color: 'bg-teal-400' },
]

// ── 使用场景 ─────────────────────────
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

<style scoped>
/* ═══════════ 动画关键帧 ═══════════ */

/* 浮动光斑 */
@keyframes floatSlow {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, -30px) scale(1.1); }
}
@keyframes floatMedium {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-25px, 20px) scale(1.05); }
}
@keyframes floatFast {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-45%, -55%) scale(1.08); }
}
@keyframes floatIcon {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.1; }
  33% { transform: translateY(-15px) rotate(5deg); opacity: 0.15; }
  66% { transform: translateY(5px) rotate(-3deg); opacity: 0.08; }
}

.floating-slow { animation: floatSlow 8s ease-in-out infinite; }
.floating-medium { animation: floatMedium 10s ease-in-out infinite; }
.floating-fast { animation: floatFast 6s ease-in-out infinite; }
.floating-icon { animation: floatIcon 7s ease-in-out infinite; }

/* 渐变文字动画 */
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
.animate-gradient {
  animation: gradientShift 4s ease-in-out infinite;
  background-size: 200% auto;
}

/* 脉冲小点 */
@keyframes pulseDot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.pulse-dot {
  animation: pulseDot 2s ease-in-out infinite;
}

/* 按钮脉冲 */
@keyframes btnPulse {
  0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
  70% { box-shadow: 0 0 0 12px rgba(59, 130, 246, 0); }
  100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}
.btn-pulse {
  animation: btnPulse 2s infinite;
}

/* ═══════════ 滚动揭示动画 ═══════════ */

.reveal-up,
.reveal-up-delayed,
.reveal-up-more,
.reveal-up-most,
.feature-card,
.step-card,
.tech-item,
.scene-card,
.stat-item {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.7s ease-out, transform 0.7s ease-out;
}

.reveal-up-delayed { transition-delay: 0.15s; }
.reveal-up-more { transition-delay: 0.3s; }
.reveal-up-most { transition-delay: 0.45s; }

/* 卡片交错延迟由模板内联 style 控制，避免 nth-child 因额外 DOM 节点失配 */

/* 可见状态 */
.reveal-up.visible,
.reveal-up-delayed.visible,
.reveal-up-more.visible,
.reveal-up-most.visible,
.feature-card.visible,
.step-card.visible,
.tech-item.visible,
.scene-card.visible,
.stat-item.visible {
  opacity: 1;
  transform: translateY(0);
}

/* 三步连接线 —— 从左向右延伸 */
.steps-line {
  opacity: 0;
  transform: scaleX(0);
  transform-origin: left center;
  transition: opacity 0.6s ease-out, transform 0.8s ease-out;
}
.steps-line.visible {
  opacity: 1;
  transform: scaleX(1);
}

/* ═══════════ 暗色模式适配 ═══════════ */
html.dark .feature-card,
html.dark .tech-item {
  background: rgba(255, 255, 255, 0.03);
}
</style>
