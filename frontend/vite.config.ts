import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
      target: process.env.VITE_API_PROXY || 'http://localhost:8000',
      changeOrigin: true,
      timeout: 600000,
      proxyTimeout: 600000,
      },
    },
  },
})
