<template>
  <div class="border-t border-gray-200 dark:border-dark-border bg-white dark:bg-dark-card px-4 py-3">
    <div class="flex items-end gap-3 max-w-4xl mx-auto">
      <!-- 输入框 -->
      <div class="flex-1 relative">
        <textarea
          ref="textareaRef"
          v-model="inputText"
          :disabled="isStreaming"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行..."
          rows="1"
          class="w-full resize-none rounded-xl border border-gray-200 dark:border-dark-border bg-white dark:bg-dark-hover px-4 py-2.5 pr-10 text-sm text-gray-800 dark:text-dark-text
                 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 outline-none
                 disabled:bg-gray-50 dark:disabled:bg-dark-hover disabled:text-gray-400 dark:disabled:text-dark-text-secondary
                 placeholder:text-gray-400 dark:placeholder:text-dark-text-secondary max-h-32"
          @keydown="handleKeydown"
          @input="autoResize"
        />
        <!-- 字符数 -->
        <span
          v-if="inputText.length > 200"
          class="absolute right-3 bottom-2 text-xs text-orange-400"
        >
          {{ inputText.length }}
        </span>
      </div>

      <!-- 发送 / 停止按钮 -->
      <button
        v-if="isStreaming"
        class="shrink-0 w-10 h-10 rounded-full bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-500
               flex items-center justify-center transition-colors"
        title="停止生成"
        aria-label="停止生成"
        @click="$emit('stop')"
      >
        <el-icon :size="18"><VideoPause /></el-icon>
      </button>
      <button
        v-else
        :disabled="!inputText.trim()"
        class="shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors
               bg-blue-500 hover:bg-blue-600 disabled:bg-gray-200 dark:disabled:bg-dark-hover disabled:cursor-not-allowed"
        title="发送"
        aria-label="发送"
        @click="send"
      >
        <el-icon :size="18" color="white"><Promotion /></el-icon>
      </button>
    </div>

    <!-- 提示文字 -->
    <p class="text-center text-xs text-gray-400 dark:text-dark-text-secondary mt-2">
      AI 助手可以帮你搜索照片、整理相册、识别内容、生成回忆
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

defineProps<{
  isStreaming: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  stop: []
}>()

const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function send() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
  nextTick(() => autoResize())
}

function handleKeydown(e: KeyboardEvent) {
  if (e.isComposing) return          // 输入法选词中，不触发发送
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 128) + 'px'
}
</script>