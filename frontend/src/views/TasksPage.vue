<template>
  <div class="p-4">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800 dark:text-dark-text">任务中心</h2>
      <el-button size="small" @click="refresh" :loading="loading">刷新</el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
      <div
        v-for="card in statCards"
        :key="card.key"
        class="rounded-lg border border-gray-200 dark:border-dark-border bg-white dark:bg-dark-card px-4 py-3"
      >
        <p class="text-xs text-gray-400 dark:text-dark-text-secondary">{{ card.label }}</p>
        <p class="text-xl font-semibold" :class="card.color">{{ card.value }}</p>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="flex flex-wrap items-center gap-3 mb-3">
      <el-select
        v-model="filterStatus"
        placeholder="全部状态"
        clearable
        size="small"
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="(meta, key) in TASK_STATUS_META"
          :key="key"
          :label="meta.label"
          :value="key"
        />
      </el-select>
      <el-select
        v-model="filterType"
        placeholder="全部类型"
        clearable
        size="small"
        style="width: 160px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="(label, key) in TASK_TYPE_LABELS"
          :key="key"
          :label="label"
          :value="key"
        />
      </el-select>
    </div>

    <!-- 任务表格 -->
    <el-table :data="tasks" v-loading="loading" border size="small" style="width: 100%">
      <el-table-column label="类型" min-width="110">
        <template #default="{ row }">
          {{ TASK_TYPE_LABELS[row.task_type] || row.task_type }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tooltip
            v-if="placeholderReason(row)"
            :content="placeholderReason(row)"
            placement="top"
          >
            <el-tag type="warning" size="small" effect="light">未接入</el-tag>
          </el-tooltip>
          <el-tag v-else :type="statusMeta(row.status).type" size="small" effect="light">
            {{ statusMeta(row.status).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="错误信息" min-width="200">
        <template #default="{ row }">
          <span v-if="row.error_message" class="text-red-500 text-xs">{{ row.error_message }}</span>
          <span v-else class="text-gray-300">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'failed'"
            type="primary"
            link
            size="small"
            @click="handleRetry(row)"
          >
            重试
          </el-button>
          <el-button
            v-if="row.status === 'pending'"
            type="danger"
            link
            size="small"
            @click="handleCancel(row)"
          >
            取消
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="flex justify-end mt-4">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        background
        @current-change="fetchTasks"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '@/api/tasks'
import { TASK_TYPE_LABELS, TASK_STATUS_META } from '@/types/task'
import type { TaskItem, TaskStats, TaskStatus } from '@/types/task'

const loading = ref(false)
const tasks = ref<TaskItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filterStatus = ref<string>('')
const filterType = ref<string>('')

const stats = ref<TaskStats>({ total: 0, pending: 0, running: 0, completed: 0, failed: 0 })

const statCards = computed(() => [
  { key: 'total', label: '总计', value: stats.value.total, color: 'text-gray-700 dark:text-dark-text' },
  { key: 'pending', label: '等待中', value: stats.value.pending, color: 'text-blue-400' },
  { key: 'running', label: '执行中', value: stats.value.running, color: 'text-blue-600' },
  { key: 'completed', label: '已完成', value: stats.value.completed, color: 'text-green-600' },
  { key: 'failed', label: '失败', value: stats.value.failed, color: 'text-red-500' },
])

function statusMeta(status: TaskStatus) {
  return TASK_STATUS_META[status] || { label: status, type: 'info' as const }
}

/** 占位任务（已完成但实际跳过）的说明，无则返回空串 */
function placeholderReason(row: TaskItem): string {
  const result = row.result as { skipped?: boolean; reason?: string } | undefined
  if (row.status === 'completed' && result?.skipped) {
    return result.reason || '该功能尚未接入'
  }
  return ''
}

/** 格式化时间 */
function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function fetchTasks() {
  loading.value = true
  try {
    const res = await taskApi.list({
      page: page.value,
      page_size: pageSize,
      status: filterStatus.value || undefined,
      task_type: filterType.value || undefined,
    })
    tasks.value = res.data.items
    total.value = res.data.total
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await taskApi.stats()
    stats.value = res.data
  } catch {
    // handled by interceptor
  }
}

function refresh() {
  fetchTasks()
  fetchStats()
}

function handleFilterChange() {
  page.value = 1
  fetchTasks()
}

async function handleRetry(row: TaskItem) {
  try {
    await taskApi.retry(row.id)
    ElMessage.success('已重新提交任务')
    refresh()
  } catch {
    // handled by interceptor
  }
}

async function handleCancel(row: TaskItem) {
  try {
    await ElMessageBox.confirm('确定取消该任务？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await taskApi.cancel(row.id)
    ElMessage.success('已取消任务')
    refresh()
  } catch {
    // handled by interceptor
  }
}

// ── 轮询：存在进行中的任务时每 4s 刷新 ─────────
let timer: ReturnType<typeof setInterval> | null = null

function ensurePolling() {
  const active = tasks.value.some((t) => t.status === 'pending' || t.status === 'running')
  if (active && !timer) {
    timer = setInterval(refreshWithPolling, 4000)
  } else if (!active && timer) {
    clearInterval(timer)
    timer = null
  }
}

async function refreshWithPolling() {
  await Promise.all([fetchTasks(), fetchStats()])
  ensurePolling()
}

onMounted(() => {
  refreshWithPolling()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
