import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  // ── 公开路由 ──────────────────────────────
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/views/LandingPage.vue'),
    meta: { title: 'AI 智能相册', noAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { title: '登录', noAuth: true },
  },
  // ── 认证路由（MainLayout 包裹）──────────
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/HomePage.vue'),
        meta: { title: '首页', icon: 'HomeFilled' },
      },
      {
        path: 'photos',
        name: 'Photos',
        component: () => import('@/views/PhotosPage.vue'),
        meta: { title: '照片', icon: 'PictureFilled' },
      },
      {
        path: 'recycle-bin',
        name: 'RecycleBin',
        component: () => import('@/views/RecycleBinPage.vue'),
        meta: { title: '回收站', icon: 'Delete' },
      },
      {
        path: 'albums',
        name: 'Albums',
        component: () => import('@/views/AlbumPage.vue'),
        meta: { title: '相册', icon: 'Folder' },
      },
      {
        path: 'faces',
        name: 'Faces',
        component: () => import('@/views/FacePage.vue'),
        meta: { title: '人物', icon: 'UserFilled' },
      },
      {
        path: 'map',
        name: 'Map',
        component: () => import('@/views/MapPage.vue'),
        meta: { title: '足迹', icon: 'Location' },
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/SearchPage.vue'),
        meta: { title: '搜索', icon: 'Search' },
      },
      {
        path: 'agent',
        name: 'Agent',
        component: () => import('@/views/AgentChat.vue'),
        meta: { title: 'AI助手', icon: 'ChatDotRound' },
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/TasksPage.vue'),
        meta: { title: '任务中心', icon: 'List' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsPage.vue'),
        meta: { title: '设置', icon: 'Setting' },
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('@/views/Training.vue'),
        meta: { title: '模型训练', icon: 'TrendCharts' },
      },
      {
        path: 'models',
        name: 'Models',
        component: () => import('@/views/Models.vue'),
        meta: { title: '模型管理', icon: 'Monitor' },
      },
      {
        path: 'database',
        name: 'Database',
        component: () => import('@/views/Database.vue'),
        meta: { title: '数据集管理', icon: 'DataBoard' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '404' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：检查登录状态
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  const token = userStore.token

  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - AI智能相册`
  }

  if (!to.meta.noAuth && !token) {
    next('/login')
  } else if (to.path === '/' && token) {
    // 已登录用户访问 Landing 页 → 跳转首页
    next('/home')
  } else if (to.path === '/login' && token) {
    next('/home')
  } else {
    next()
  }
})

export default router
