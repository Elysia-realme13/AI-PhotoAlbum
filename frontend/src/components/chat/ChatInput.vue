<template>
  <div class="border-t border-gray-200 dark:border-dark-border bg-white dark:bg-dark-card px-4 py-3">
    <!-- 图片预览 -->
    <div v-if="selectedImage" class="mb-2 max-w-4xl mx-auto">
      <div class="inline-flex items-start gap-2 bg-gray-50 dark:bg-dark-hover rounded-lg p-2">
        <img :src="imagePreviewUrl" class="h-16 w-16 object-cover rounded" />
        <button
          class="w-5 h-5 rounded-full bg-gray-300 dark:bg-gray-600 hover:bg-red-400 flex items-center justify-center text-white text-xs shrink-0"
          title="移除图片"
          @click="removeImage"
        >
          &times;
        </button>
      </div>
    </div>

    <div class="flex items-end gap-3 max-w-4xl mx-auto">
      <!-- 上传图片按钮 -->
      <button
        class="shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors
               bg-gray-100 dark:bg-dark-hover hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 dark:text-dark-text-secondary"
        title="上传图片搜索"
        aria-label="上传图片搜索"
        :disabled="isStreaming"
        @click="triggerFileInput"
      >
        <el-icon :size="18"><Picture /></el-icon>
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        class="hidden"
        @change="handleFileChange"
      />

      <!-- 输入框 -->
      <div class="flex-1 relative">
        <textarea
          ref="textareaRef"
          v-model="inputText"
          :disabled="isStreaming"
          :placeholder="selectedImage ? '描述这张图片...' : '输入消息，Enter 发送，Shift+Enter 换行...'"
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
import { ref, nextTick, watch } from 'vue'
import { Picture, VideoPause, Promotion } from '@element-plus/icons-vue'

defineProps<{
  isStreaming: boolean
}>()

const emit = defineEmits<{
  send: [text: string, image?: File]
  stop: []
}>()

const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedImage = ref<File | null>(null)
const imagePreviewUrl = ref<string>('')

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  selectedImage.value = file
  imagePreviewUrl.value = URL.createObjectURL(file)
}

function removeImage() {
  selectedImage.value = null
  if (imagePreviewUrl.value) {
    URL.revokeObjectURL(imagePreviewUrl.value)
  }
  imagePreviewUrl.value = ''
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function send() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text, selectedImage.value || undefined)
  inputText.value = ''
  removeImage()
  nextTick(() => autoResize())
}

function handleKeydown(e: KeyboardEvent) {
  if (e.isComposing) return
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