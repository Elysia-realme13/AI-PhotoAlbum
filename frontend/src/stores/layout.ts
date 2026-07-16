import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useLayoutStore = defineStore('layout', () => {
  // 侧边栏是否展开
  const sidebarExpanded = ref(true)

  function toggleSidebar() {
    sidebarExpanded.value = !sidebarExpanded.value
    localStorage.setItem('sidebarExpanded', String(sidebarExpanded.value))
  }

  // 从缓存恢复
  const cachedState = localStorage.getItem('sidebarExpanded')
  if (cachedState !== null) {
    sidebarExpanded.value = cachedState === 'true'
  }

  return { sidebarExpanded, toggleSidebar }
})
