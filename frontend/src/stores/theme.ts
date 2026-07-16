import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<ThemeMode>('light')

  function applyTheme(mode: ThemeMode) {
    const html = document.documentElement
    if (mode === 'dark') {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  function setTheme(mode: ThemeMode) {
    theme.value = mode
    applyTheme(mode)
    localStorage.setItem('theme', mode)
  }

  function toggleTheme() {
    setTheme(theme.value === 'light' ? 'dark' : 'light')
  }

  // 从缓存恢复
  const cachedTheme = localStorage.getItem('theme') as ThemeMode | null
  if (cachedTheme) {
    theme.value = cachedTheme
    applyTheme(cachedTheme)
  }

  // 监听变化，同步到 DOM
  watch(theme, (val) => applyTheme(val))

  return { theme, setTheme, toggleTheme }
})
