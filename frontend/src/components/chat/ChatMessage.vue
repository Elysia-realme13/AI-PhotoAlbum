<template>
  <div :class="['flex gap-3 mb-4', msg.role === 'user' ? 'flex-row-reverse' : '']">
    <!-- 头像 -->
    <div class="shrink-0">
      <div
        v-if="msg.role === 'assistant'"
        class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center"
      >
        <el-icon :size="16" color="white"><ChatDotRound /></el-icon>
      </div>
      <div
        v-else
        class="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center"
      >
        <el-icon :size="16" color="white"><UserFilled /></el-icon>
      </div>
    </div>

    <!-- 消息内容 -->
    <div
      :class="[
        'max-w-[75%] rounded-xl px-4 py-3',
        msg.role === 'user'
          ? 'bg-blue-500 text-white'
          : 'bg-white border border-gray-100 shadow-sm text-gray-800',
      ]"
    >
      <!-- Markdown 渲染（AI 消息） -->
      <div
        v-if="msg.role === 'assistant'"
        class="markdown-body text-sm"
        v-html="renderedContent"
      />

      <!-- 用户消息纯文本 -->
      <p v-else class="text-sm whitespace-pre-wrap">{{ msg.content }}</p>

      <!-- 用户上传的图片 -->
      <img
        v-if="msg.role === 'user' && msg.imageUrl"
        :src="msg.imageUrl"
        class="mt-2 max-w-48 max-h-48 rounded-lg object-cover"
      />

      <!-- 流式输出光标 -->
      <span
        v-if="msg.streaming"
        class="inline-block w-2 h-4 bg-blue-500 align-middle ml-0.5 animate-pulse rounded-sm"
      />

      <!-- 名称确认对话框 -->
      <NameConfirmDialog
        v-if="msg.nameConfirm && !msg.nameConfirm.confirmed"
        :candidates="msg.nameConfirm.candidates"
        :person-name="msg.nameConfirm.personName"
        :session-id="sessionId || ''"
        :query="msg.nameConfirm.personName"
        @confirmed="handleNameConfirmed"
        @skip="handleNameSkip"
      />
      <div
        v-else-if="msg.nameConfirm && msg.nameConfirm.confirmed"
        class="mt-2 text-xs text-green-600 dark:text-green-400 flex items-center gap-1"
      >
        <el-icon><CircleCheck /></el-icon>
        已将「{{ msg.nameConfirm.personName }}」绑定到选定的人脸聚类
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import type { ChatMessage } from '@/types/chat'
import NameConfirmDialog from './NameConfirmDialog.vue'

const props = withDefaults(defineProps<{
  msg: ChatMessage
  sessionId?: string
}>(), {
  sessionId: '',
})

const emit = defineEmits<{
  (e: 'nameConfirmed', data: { cluster_id: string; name: string; messageId: string }): void
  (e: 'nameSkip', data: { messageId: string }): void
}>()

function handleNameConfirmed(data: { cluster_id: string; name: string }) {
  emit('nameConfirmed', { ...data, messageId: props.msg.id })
}

function handleNameSkip() {
  emit('nameSkip', { messageId: props.msg.id })
}

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const renderedContent = computed(() => {
  if (!props.msg.content) return ''
  return md.render(props.msg.content)
})
</script>

<style scoped>
/* 覆盖 markdown 默认样式 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  font-weight: 600;
  margin: 0.5em 0 0.25em;
}
.markdown-body :deep(h1) { font-size: 1.2em; }
.markdown-body :deep(h2) { font-size: 1.1em; }
.markdown-body :deep(h3) { font-size: 1em; }
.markdown-body :deep(p) {
  margin: 0.25em 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.2em;
  margin: 0.25em 0;
}
.markdown-body :deep(li) {
  margin: 0.1em 0;
}
.markdown-body :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 0.15em 0.3em;
  border-radius: 3px;
  font-size: 0.9em;
}
.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 0.75em 1em;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5em 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.4em 0.75em;
  text-align: left;
  font-size: 0.9em;
}
.markdown-body :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}
.markdown-body :deep(a) {
  color: #409eff;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #e5e7eb;
  padding-left: 0.75em;
  color: #6b7280;
  margin: 0.5em 0;
}
.markdown-body :deep(strong) {
  font-weight: 600;
}
</style>