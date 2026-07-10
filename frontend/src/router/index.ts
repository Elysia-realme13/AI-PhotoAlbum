import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { title: '登录', noAuth: true },
  },
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
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsPage.vue'),
        meta: { title: '设置', icon: 'Setting' },
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
  const token = localStorage.getItem('token')
  if (!to.meta.noAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/home')
  } else {
    next()
  }
})

export default router
