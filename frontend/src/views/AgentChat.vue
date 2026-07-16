<template>
  <div class="agent-chat flex h-full">
    <!-- ── 左侧对话列表 ── -->
    <aside
      :class="[
        'flex flex-col shrink-0 bg-white dark:bg-dark-card border-r border-gray-200 dark:border-dark-border transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-0 overflow-hidden border-r-0',
      ]"
    >
      <!-- 新建对话 -->
      <div class="p-3">
        <el-button type="primary" class="w-full" :icon="Plus" @click="handleNewChat">
          新建对话
        </el-button>
      </div>

      <!-- 对话列表 -->
      <div class="flex-1 overflow-y-auto px-2">
        <!-- 加载态 -->
        <template v-if="store.loadingConversations">
          <div v-for="i in 3" :key="i" class="mx-1 mb-2 p-3 rounded-lg">
            <div class="h-4 bg-gray-200 rounded w-3/4 mb-2 animate-pulse" />
            <div class="h-3 bg-gray-200 rounded w-1/2 animate-pulse" />
          </div>
        </template>

        <!-- 空状态 -->
        <div v-else-if="store.conversations.length === 0" class="text-center py-8">
          <el-icon :size="32" color="#d0d5dd"><ChatDotRound /></el-icon>
          <p class="text-sm text-gray-400 mt-2">暂无对话记录</p>
          <p class="text-xs text-gray-300 mt-1">开始和 AI 对话吧</p>
        </div>

        <!-- 对话列表 -->
        <div
          v-for="conv in store.conversations"
          :key="conv.id"
          :class="[
            'mb-1 p-3 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-dark-hover group',
            store.currentConversationId === conv.id ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800' : '',
          ]"
          @click="handleSelectConversation(conv.id)"
        >
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium text-gray-800 dark:text-dark-text truncate flex-1 min-w-0">{{ conv.title }}</div>
            <button
              class="shrink-0 ml-1 w-6 h-6 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-all"
              title="删除对话"
              aria-label="删除对话"
              @click.stop="handleDeleteConversation(conv.id)"
            >
              <el-icon :size="14"><Delete /></el-icon>
            </button>
          </div>
          <div class="flex items-center justify-between mt-1">
            <span class="text-xs text-gray-400">{{ conv.message_count }} 条消息</span>
            <span class="text-xs text-gray-400">{{ formatConvTime(conv.updated_at) }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- ── 主聊天区域 ── -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 顶部栏 -->
      <header class="h-12 shrink-0 flex items-center px-4 border-b border-gray-200 dark:border-dark-border bg-white dark:bg-dark-card">
        <!-- 侧边栏切换 -->
        <button
          class="w-8 h-8 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover flex items-center justify-center mr-3 shrink-0"
          aria-label="切换对话列表"
          @click="sidebarOpen = !sidebarOpen"
        >
          <el-icon :size="18"><Fold /></el-icon>
        </button>

        <!-- 标题 -->
        <div class="flex-1 min-w-0 flex items-center gap-2">
          <el-icon :size="16" color="#409EFF"><ChatDotRound /></el-icon>
          <h2 v-if="store.currentConversation" class="text-sm font-medium text-gray-800 dark:text-dark-text truncate">
            {{ store.currentConversation.title }}
          </h2>
          <h2 v-else class="text-sm font-medium text-gray-800 dark:text-dark-text">AI 助手</h2>
        </div>

        <!-- 模型信息 -->
        <span class="text-xs text-gray-400 dark:text-dark-text-secondary shrink-0">AI 智能相册助手</span>
      </header>

      <!-- 消息区域 -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto px-4 py-4">
        <!-- 消息列表 -->
        <div v-if="store.messages.length > 0" class="max-w-4xl mx-auto">
          <ChatMessage
            v-for="msg in store.messages"
            :key="msg.id"
            :msg="msg"
            :session-id="store.currentConversationId || ''"
            @name-confirmed="handleNameConfirmed"
            @name-skip="handleNameSkipped"
          />

          <!-- 滚动锚点 -->
          <div ref="scrollAnchor" />
        </div>

        <!-- 欢迎状态 -->
        <div v-if="isWelcome" class="h-full flex items-center justify-center">
          <div class="text-center max-w-sm">
            <div class="w-20 h-20 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center mx-auto mb-6">
              <el-icon :size="36" color="#409EFF"><ChatDotRound /></el-icon>
            </div>
            <h3 class="text-xl font-semibold text-gray-800 dark:text-dark-text mb-2">AI 智能相册助手</h3>
            <p class="text-sm text-gray-500 dark:text-dark-text-secondary mb-6">我是你的专属相册管家，可以帮你搜索照片、整理相册、识别内容和生成回忆。</p>

            <!-- 建议问题 -->
            <div class="grid grid-cols-1 gap-2">
              <button
                v-for="q in suggestedQuestions"
                :key="q"
                class="text-left px-4 py-2.5 rounded-xl border border-gray-200 dark:border-dark-border hover:border-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-sm text-gray-700 dark:text-dark-text-secondary transition-colors"
                @click="store.sendMessage(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <ChatInput
        :is-streaming="store.isStreaming"
        @send="(text, image) => store.sendMessage(text, image)"
        @stop="store.cancelStream"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { Plus, Fold, Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const store = useChatStore()

// ── 侧边栏 ──
const sidebarOpen = ref(true)

// ── 滚动控制 ──
const messagesContainer = ref<HTMLElement | null>(null)
const scrollAnchor = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    scrollAnchor.value?.scrollIntoView({ behavior: 'instant' })
  })
}

// 监听消息变化自动滚动
watch(
  () => store.messages.length,
  () => scrollToBottom()
)
// 流式输出时持续滚动
watch(
  () => store.streamingContent,
  () => scrollToBottom()
)

// ── 欢迎状态 ──
const isWelcome = computed(
  () => store.messages.length === 0 && !store.loadingMessages
)

// ── 建议问题 ──
const suggestedQuestions = [
  '帮我找一下去年夏天在海边的照片',
  '整理我的旅游照片创建一个新相册',
  '生成 2024 年我的年度精彩回顾',
  '分析一下最近上传的风景照片',
]

// ── 格式化时间 ──
function formatConvTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  return `${date.getMonth() + 1}/${date.getDate()}`
}

// ── 操作 ──
function handleNewChat() {
  store.newConversation()
  nextTick(() => scrollToBottom())
}

function handleSelectConversation(id: string) {
  if (store.isStreaming) return
  store.fetchMessages(id)
}

async function handleDeleteConversation(id: string) {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？删除后不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.deleteConversation(id)
  } catch {
    // 取消
  }
}

function handleNameConfirmed(data: { cluster_id: string; name: string; messageId: string }) {
  store.markNameConfirmed(data.messageId)
  nextTick(() => scrollToBottom())
}

function handleNameSkipped(data: { messageId: string }) {
  store.markNameSkipped(data.messageId)
}

// ── 初始化 ──
onMounted(() => {
  store.fetchConversations()
})

// ── 卸载时中断进行中的流式输出，避免定时器泄漏 ──
onBeforeUnmount(() => {
  if (store.isStreaming) store.cancelStream()
})
</script>

<style scoped>
.agent-chat {
  /* 使用负 margin 抵消 MainLayout 的 padding，使聊天界面铺满 */
  margin: -24px;
  /* 高度依赖：AppHeader h-14(56px) + MainLayout main 的 p-6(上下各 24px) */
  height: calc(100vh - 56px - 24px - 24px);
}

/* 消息区域自定义滚动条 */
.agent-chat :deep(::-webkit-scrollbar) {
  width: 5px;
}
.agent-chat :deep(::-webkit-scrollbar-thumb) {
  background: #e5e7eb;
  border-radius: 3px;
}
.agent-chat :deep(::-webkit-scrollbar-track) {
  background: transparent;
}
</style>