<template>
  <div class="h-full flex flex-col space-y-4">
    <!-- 页面标题与操作栏 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <el-button v-if="selectedTask" size="small" @click="selectedTaskId = null">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
      <h2 class="text-xl font-bold text-gray-800 dark:text-dark-text">模型训练</h2>
      </div>
      <div class="flex items-center space-x-3">
        <el-button type="primary" @click="createDialogVisible = true">
          <el-icon><Plus /></el-icon> 新建训练
        </el-button>
        <el-button @click="refreshTaskList">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="flex flex-1 gap-4 overflow-hidden">
      <!-- 右侧：监控面板 -->
      <div v-if="selectedTask" class="flex-1 flex flex-col space-y-3 overflow-hidden">
        <!-- 任务信息栏 -->
        <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-3 flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <span class="font-semibold text-gray-800 dark:text-dark-text">{{ selectedTask.task_name }}</span>
           <el-tag :type="statusType(selectedTask.status)" size="small">{{ statusLabel(selectedTask.status) }}</el-tag>
            <span class="text-sm text-gray-500 dark:text-dark-text-secondary" v-if="selectedTask.dataset_name">
              数据集: <strong>{{ selectedTask.dataset_name }}</strong>
            </span>
           <span class="text-sm text-gray-500 dark:text-dark-text-secondary">Epoch: {{ epochDisplay(selectedTask.current_epoch, selectedTask.total_epochs, selectedTask.status) }}</span>
            <span class="text-sm text-gray-500 dark:text-dark-text-secondary" v-if="selectedTask.best_metric !== null">
              最佳 mAP50: <strong>{{ selectedTask.best_metric.toFixed(4) }}</strong>
            </span>
          </div>
         <div class="flex space-x-2">
           <el-button v-if="selectedTask.status === 'pending' || selectedTask.status === 'failed'"
              type="primary" size="small" @click="startTask" :loading="controlLoading">
              <el-icon><VideoPlay /></el-icon> 开始训练
            </el-button>
            <el-button v-if="selectedTask.status === 'running'" type="warning" size="small" @click="pauseTask" :loading="controlLoading">
              <el-icon><VideoPause /></el-icon> 暂停
            </el-button>
            <el-button v-if="selectedTask.status === 'paused'" type="success" size="small" @click="resumeTask" :loading="controlLoading">
              <el-icon><VideoPlay /></el-icon> 恢复
            </el-button>
            <el-button v-if="selectedTask.status === 'running' || selectedTask.status === 'paused'"
              type="danger" size="small" @click="confirmStop">
              <el-icon><VideoPause /></el-icon> 停止
            </el-button>
            <el-button v-if="selectedTask.status === 'completed' || selectedTask.status === 'failed'"
              type="danger" size="small" plain @click="confirmDelete">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </div>
        </div>

        <!-- 进度条 -->
        <div v-if="selectedTask.total_epochs > 0" class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-3">
          <el-progress :percentage="progressPercent" :stroke-width="16" :text-inside="true"
            :status="progressStatus" />
        </div>

        <!-- 指标图表 -->
        <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-3 flex-1 min-h-0" v-if="metricLines.length > 0">
          <v-chart :option="chartOption" autoresize class="w-full h-full" />
        </div>
        <div v-else class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-3 flex-1 min-h-0 flex items-center justify-center text-gray-400 dark:text-dark-text-secondary">
          <div class="text-center">
            <el-icon :size="48"><ChatLineSquare /></el-icon>
            <p class="mt-2">暂无指标数据，开始训练后将实时显示</p>
          </div>
        </div>

        <!-- 可拖动的分隔线 -->
        <div
          class="h-1.5 bg-gray-200 dark:bg-dark-border rounded cursor-row-resize hover:bg-blue-300 active:bg-blue-400 flex-shrink-0"
          @mousedown.prevent="startLogDrag"
        />

        <!-- 日志输出 -->
        <div
          ref="logContainer"
          class="bg-white dark:bg-gray-800 rounded-lg p-3 overflow-y-auto font-mono text-xs text-gray-700 dark:text-gray-200 flex-shrink-0"
          :style="{ height: logHeight + 'px' }"
          @mousedown="(e: MouseEvent) => e.stopPropagation()"
        >
          <div v-if="logLines.length === 0" class="text-gray-500 dark:text-dark-text-secondary">等待训练日志输出...</div>
          <div v-for="(line, i) in logLines" :key="i" class="leading-5">{{ line }}</div>
        </div>
 </div>

      <!-- 未选择任务时的引导 -->
      <div v-else class="flex-1 flex flex-col gap-4 overflow-y-auto p-2">
        <!-- 任务统计卡片 -->
        <div class="grid grid-cols-4 gap-4">
          <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-4 text-center">
            <div class="text-sm text-gray-500 dark:text-dark-text-secondary mb-1">全部任务</div>
            <div class="text-2xl font-bold text-blue-600">{{ taskStats.total }}</div>
          </div>
          <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-4 text-center">
            <div class="text-sm text-gray-500 dark:text-dark-text-secondary mb-1">训练中</div>
            <div class="text-2xl font-bold text-yellow-600">{{ taskStats.running }}</div>
          </div>
          <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-4 text-center">
            <div class="text-sm text-gray-500 dark:text-dark-text-secondary mb-1">已完成</div>
            <div class="text-2xl font-bold text-green-600">{{ taskStats.completed }}</div>
          </div>
          <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-4 text-center">
            <div class="text-sm text-gray-500 dark:text-dark-text-secondary mb-1">失败</div>
            <div class="text-2xl font-bold text-red-600">{{ taskStats.failed }}</div>
          </div>
        </div>
        <!-- 最近任务列表 -->
        <div class="bg-white dark:bg-dark-card rounded-lg border border-gray-100 dark:border-dark-border p-3 flex-1 overflow-y-auto max-h-[420px]">
          <h4 class="text-sm font-semibold text-gray-700 dark:text-dark-text mb-3">最近训练任务</h4>
          <el-table :data="taskList" empty-text="暂无训练任务" style="width: 100%"
            @row-click="(row:any) => onTaskSelect(row.id)" highlight-current-row>
           <el-table-column prop="task_name" label="任务" min-width="120" />
            <el-table-column prop="dataset_name" label="数据集" min-width="120" />
           <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="90" align="center">
              <template #default="{ row }">{{ epochDisplay(row.current_epoch, row.total_epochs, row.status) }}</template>
            </el-table-column>
            <el-table-column prop="best_metric" label="mAP50" width="90" align="center">
              <template #default="{ row }">{{ row.best_metric?.toFixed(4) || '-' }}</template>
            </el-table-column>
          </el-table>
        </div>
        <!-- 快速操作提示 -->
        <div class="bg-blue-50 rounded-lg border border-blue-200 p-3 text-sm text-blue-700">
          点击上方「新建训练」开始一个新的训练任务，或在下方列表中点击任务卡片以查看训练详情和指标。
        </div>
      </div>
    </div>

    <!-- 创建训练任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建训练任务" width="650px" top="3vh" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px" size="small">
        <!-- 基础信息 -->
        <el-divider content-position="left">基础信息</el-divider>
        <el-form-item label="任务名称" required>
          <el-input v-model="form.task_name" placeholder="如：我的家庭相册检测模型" />
        </el-form-item>
        <el-form-item label="模型命名" required>
          <el-input v-model="form.model_name" placeholder="如：family_v1" />
        </el-form-item>
        <el-form-item label="训练描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="对本次训练任务的说明（选填）" />
        </el-form-item>

        <!-- 数据集配置 -->
        <el-divider content-position="left">数据集配置</el-divider>
        <el-form-item label="数据来源" required>
          <el-radio-group v-model="datasetMode">
            <el-radio value="select">选择已有数据集</el-radio>
            <el-radio value="upload">上传新数据集</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="datasetMode === 'select'" label="数据集" required>
          <el-select v-model="form.dataset_id" placeholder="选择已有数据集" clearable style="width: 100%">
            <el-option v-for="ds in datasetList" :key="ds.id" :label="`${ds.name} (${ds.image_count}张, ${ds.class_count}类)`" :value="ds.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="datasetMode === 'upload'" label="数据集文件" required>
          <div class="flex items-center space-x-3 w-full">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleFileChange"
              accept=".zip,.tar,.tar.gz,.tgz,.tar.bz2,.7z,.rar"
              :limit="1"
            >
              <el-button type="primary">
                <el-icon><UploadFilled /></el-icon>
                {{ datasetFile ? '重新选择' : '选择文件' }}
              </el-button>
            </el-upload>
            <span v-if="datasetFile" class="text-sm text-gray-600">{{ datasetFile.name }}</span>
            <span v-else class="text-sm text-gray-400 dark:text-dark-text-secondary">支持 .zip / .tar / .tar.gz / .7z / .rar</span>
          </div>
        </el-form-item>
        <el-form-item label="验证集比例">
          <el-slider v-model="form.config.val_split" :min="0" :max="0.5" :step="0.05" show-input style="width: 180px" />
        </el-form-item>
        <el-form-item label="使用默认划分">
          <el-switch v-model="form.config.use_dataset_split" />
          <span class="text-gray-400 text-xs ml-2 dark:text-dark-text-secondary">使用原数据集默认的 train/val 划分</span>
        </el-form-item>

        <!-- 模型参数 -->
        <el-divider content-position="left">模型参数</el-divider>
        <el-form-item label="预训练模型">
          <el-select v-model="form.config.pretrained_model" placeholder="选择预训练模型" style="width: 100%">
            <el-option label="YOLO26（默认）" value="yolo26n.pt" />
            <el-option v-for="m in trainedModels" :key="m.model_name" :label="m.model_name" :value="m.file_path || (m.model_name + '.pt')" />
          </el-select>
        </el-form-item>
        <el-row :gutter="8">
          <el-col :span="8">
            <el-form-item label="imgsz" label-width="50px">
              <el-input-number v-model="form.config.imgsz" :min="320" :max="1280" :step="32" controls-position="right" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="epochs" label-width="55px">
              <el-input-number v-model="form.config.epochs" :min="1" :max="1000" controls-position="right" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="batch" label-width="50px">
              <el-input-number v-model="form.config.batch" :min="1" :max="256" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="8">
          <el-col :span="12">
            <el-form-item label="学习率" label-width="60px">
              <el-input-number v-model="form.config.lr0" :min="0.0001" :max="0.1" :step="0.001" :precision="4" controls-position="right" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优化器" label-width="60px">
              <el-select v-model="form.config.optimizer">
                <el-option label="SGD" value="SGD" />
                <el-option label="Adam" value="Adam" />
                <el-option label="AdamW" value="AdamW" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 高级选项（可折叠） -->
        <el-collapse>
          <el-collapse-item title="高级选项" name="advanced">
            <el-row :gutter="8">
              <el-col :span="12">
                <el-form-item label="动量" label-width="50px">
                  <el-input-number v-model="form.config.momentum" :min="0" :max="1" :step="0.01" :precision="3" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="权重衰减" label-width="70px">
                  <el-input-number v-model="form.config.weight_decay" :min="0" :max="0.1" :step="0.0001" :precision="4" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="8">
              <el-col :span="12">
                <el-form-item label="预热轮数" label-width="70px">
                  <el-input-number v-model="form.config.warmup_epochs" :min="0" :max="50" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="工作线程" label-width="70px">
                  <el-input-number v-model="form.config.workers" :min="0" :max="32" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="8">
              <el-col :span="12">
                <el-form-item label="随机种子" label-width="70px">
                  <el-input-number v-model="form.config.seed" :min="0" :max="99999" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="保存间隔" label-width="70px">
                  <el-input-number v-model="form.config.save_period" :min="-1" :max="100" controls-position="right" />
                  <span class="text-gray-400 text-xs ml-1 dark:text-dark-text-secondary">(-1 仅保存最后)</span>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="早停耐心">
              <el-input-number v-model="form.config.patience" :min="0" :max="500" controls-position="right" />
              <span class="text-gray-400 text-xs ml-2 dark:text-dark-text-secondary">验证集 loss 连续 N 轮不下降则停止</span>
            </el-form-item>
            <el-divider content-position="left">数据增强</el-divider>
            <el-form-item label="多尺度训练">
              <el-switch v-model="form.config.multi_scale" />
            </el-form-item>
            <el-form-item label="MixUp">
              <el-slider v-model="form.config.mixup" :min="0" :max="1" :step="0.1" show-input style="width: 180px" />
            </el-form-item>
            <el-form-item label="Mosaic">
              <el-slider v-model="form.config.mosaic" :min="0" :max="1" :step="0.1" show-input style="width: 180px" />
            </el-form-item>
            <el-form-item label="Copy-Paste">
              <el-slider v-model="form.config.copy_paste" :min="0" :max="1" :step="0.1" show-input style="width: 180px" />
            </el-form-item>
            <el-divider content-position="left">硬件配置</el-divider>
            <el-form-item label="设备选择">
              <el-radio-group v-model="form.config.device">
                <el-radio value="">自动检测</el-radio>
                <el-radio value="cpu">CPU</el-radio>
                <el-radio value="0">CUDA:0</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">
          <el-icon><Check /></el-icon> 创建任务
        </el-button>
      </template>
    </el-dialog>

    <!-- 停止确认对话框 -->
    <el-dialog v-model="stopDialogVisible" title="确认停止训练" width="400px">
      <p>确定要停止当前训练吗？</p>
      <p class="text-sm text-red-500 mt-2">停止后当前未完成的 checkpoint 将不会被保存。</p>
      <template #footer>
        <el-button @click="stopDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="stopTask" :loading="controlLoading">确认停止</el-button>
      </template>
    </el-dialog>

    <!-- 删除确认对话框 -->
    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="400px">
      <p>确定要删除训练任务 "{{ selectedTask?.task_name }}" 吗？</p>
      <p class="text-sm text-red-500 mt-2">删除后对应的模型文件和训练记录将被永久移除。</p>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="deleteTask" :loading="controlLoading">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import trainingApi, { type CreateTaskParams, type TrainingTask, type MetricItem, type DatasetItem } from '@/api/training'

// 注册 ECharts 组件
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

// ── 状态变量 ─────────────────────────────────────────────────────

const createDialogVisible = ref(false)
const creating = ref(false)
const controlLoading = ref(false)
const stopDialogVisible = ref(false)
const deleteDialogVisible = ref(false)
const selectedTaskId = ref<string | null>(null)
const taskList = ref<TrainingTask[]>([])
const datasetList = ref<DatasetItem[]>([])
const metricsData = ref<MetricItem[]>([])
const logLines = ref<string[]>([])
const logHeight = ref(160)
const logDragging = ref(false)
let logDragStartY = 0
let logDragStartHeight = 160
const logContainer = ref<HTMLElement | null>(null)
const isDark = ref(document.documentElement.classList.contains('dark'))
const pollTimer = ref<number | null>(null)
const datasetMode = ref<'select' | 'upload'>('select')
const datasetFile = ref<File | null>(null)
const uploadRef = ref()
const trainedModels = ref<{ model_name: string; file_path: string | null }[]>([])

const defaultConfig = {
  pretrained_model: 'yolo26n.pt',
  imgsz: 640,
  epochs: 100,
  batch: 16,
  lr0: 0.01,
  optimizer: 'AdamW',
  momentum: 0.937,
  weight_decay: 0.0005,
  warmup_epochs: 3,
  multi_scale: false,
  mixup: 0,
  mosaic: 1,
  copy_paste: 0,
  device: '',
  workers: 8,
  seed: 0,
  save_period: -1,
  patience: 50,
  val_split: 0.2,
  use_dataset_split: false,
}

const form = ref<CreateTaskParams>({
  task_name: '',
  model_name: '',
  description: '',
  dataset_id: undefined,
  config: { ...defaultConfig },
})

// ── 计算属性 ─────────────────────────────────────────────────────
const taskStats = computed(() => {
  const stats = { total: taskList.value.length, running: 0, completed: 0, failed: 0, paused: 0, pending: 0 }
  for (const t of taskList.value) {
    if (stats[t.status as keyof typeof stats] !== undefined)
      stats[t.status as keyof typeof stats]++
  }
  return stats
})

const selectedTask = computed(() => {
  if (!selectedTaskId.value) return null
  return taskList.value.find(t => t.id === selectedTaskId.value) || null
})

const progressPercent = computed(() => {
  if (!selectedTask.value) return 0
  const t = selectedTask.value
  if (t.total_epochs === 0) return 0
  const done = t.status === "pending" ? 0 : Math.min(t.current_epoch + 1, t.total_epochs)
  return Math.round((done / t.total_epochs) * 100)
})

function epochDisplay(current: number, total: number, status: string): string {
  if (status === "pending" && current === 0) return `0 / ${total}`
  const done = Math.min(current + 1, total)
  return `${done} / ${total}`
}

const progressStatus = computed(() => {
  if (!selectedTask.value) return '' as any
  const status = selectedTask.value.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return '' as any
})

const metricLines = computed(() => {
  const keys = new Set<string>()
  for (const m of metricsData.value) {
    for (const k of Object.keys(m.metrics)) {
      keys.add(k)
    }
  }
  // 只显示关键指标
  const importantKeys = [
    'train/box_loss', 'train/cls_loss', 'train/dfl_loss',
    'val/box_loss', 'val/cls_loss', 'val/dfl_loss',
    'metrics/mAP50', 'metrics/mAP50-95', 'metrics/recall', 'metrics/precision',
  ]
  const lines = importantKeys.filter(k => keys.has(k))
  // 如果没有关键指标，显示所有
  return lines.length > 0 ? lines : Array.from(keys)
})

const chartOption = computed(() => {
  if (metricsData.value.length === 0) return {}

  const epochs = metricsData.value.map(m => m.epoch)
  const series = metricLines.value.map(key => ({
    name: key,
    type: 'line' as const,
    smooth: true,
    symbol: 'none',
    data: metricsData.value.map(m => m.metrics[key] ?? null),
  }))

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        let html = `<b>Epoch ${params[0]?.axisValue}</b><br/>`
        for (const p of params) {
          if (p.value !== null) {
            html += `${p.marker} ${p.seriesName}: <b>${Number(p.value).toFixed(4)}</b><br/>`
          }
        }
        return html
      },
    },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 50, right: 20, top: 40, bottom: 45 },
    xAxis: {
      type: 'category',
      data: epochs,
      name: 'Epoch',
      nameLocation: 'end',
      nameGap: 5,
    },
    yAxis: {
      type: 'value',
      name: 'Value',
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 18, bottom: 2 },
    ],
    series,
  }
})

// ── 辅助函数 ─────────────────────────────────────────────────────

function statusType(status: string) {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    paused: '',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待开始',
    running: '训练中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

// ── 数据加载 ─────────────────────────────────────────────────────

async function loadTaskList() {
  try {
    const res = await trainingApi.listTasks()
    taskList.value = res.data.items
  } catch {
    // 忽略
  }
}

async function loadDatasets() {
  try {
    const res = await trainingApi.listDatasets()
    datasetList.value = res.data.items
  } catch {
    // 忽略
  }
}

async function loadMetrics(taskId: string) {
  try {
    const res = await trainingApi.getTaskDetail(taskId)
    if (selectedTaskId.value !== taskId) return
    metricsData.value = res.data.metrics || []
    logLines.value = res.data.logs || []

    // 更新 taskList 中的状态
    const idx = taskList.value.findIndex(t => t.id === taskId)
    if (idx >= 0) {
      taskList.value[idx] = res.data.task
    }
  } catch {
    // 忽略
  }
}

// ── 操作函数 ─────────────────────────────────────────────────────

async function refreshTaskList() {
  await Promise.all([loadTaskList(), loadDatasets()])
}

async function onTaskSelect(taskId: string) {
  if (!taskId) {
    selectedTaskId.value = null
    return
  }
  selectedTaskId.value = taskId
  stopPolling()
  logLines.value = []
  await loadMetrics(taskId)

  // 如果任务正在运行，启动轮询
  const task = taskList.value.find(t => t.id === taskId)
  if (task && (task.status === 'running' || task.status === 'paused')) {
    startPolling(taskId)
  }
}

async function createTask() {
  if (!form.value.task_name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (!form.value.model_name.trim()) {
    ElMessage.warning('请输入模型名称')
    return
  }
  if (datasetMode.value === 'select' && !form.value.dataset_id) {
    ElMessage.warning('请选择数据集')
    return
  }
  if (datasetMode.value === 'upload' && !datasetFile.value) {
    ElMessage.warning('请选择数据集文件')
    return
  }
  if (datasetMode.value === 'upload' && datasetFile.value) {
    const fileName = datasetFile.value.name
    const lower = fileName.toLowerCase()
    const stem = lower.endsWith('.tar.gz') || lower.endsWith('.tgz') ? fileName.slice(0, -7)
      : lower.endsWith('.tar.bz2') ? fileName.slice(0, -8)
      : (fileName.lastIndexOf('.') > 0 ? fileName.slice(0, fileName.lastIndexOf('.')) : fileName)
    if (datasetList.value.some(ds => ds.name === stem)) {
      ElMessage.warning('数据集 "' + stem + '" 已存在，请勿重复上传')
      return
    }
  }

 creating.value = true
 try {
    let res
    if (datasetMode.value === 'upload' && datasetFile.value) {
      const loadingInstance = ElLoading.service({ lock: true, text: '正在上传数据集，请稍候...', background: 'rgba(0,0,0,0.7)' })
      try {
        res = await trainingApi.createTaskWithDataset({
          file: datasetFile.value,
          task_name: form.value.task_name,
          model_name: form.value.model_name,
          description: form.value.description || undefined,
          config: form.value.config,
        })
      } finally {
        loadingInstance.close()
      }
    } else {
      res = await trainingApi.createTask({ ...form.value })
    }
    ElMessage.success('训练任务创建成功')
    createDialogVisible.value = false
    await loadTaskList()
    selectedTaskId.value = res.data.id
    await onTaskSelect(res.data.id)

    // 重置表单
    form.value = {
      task_name: '',
      model_name: '',
      description: '',
      dataset_id: undefined,
      config: { ...defaultConfig },
    }
    datasetFile.value = null
    datasetMode.value = 'select'
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '创建任务失败')
  } finally {
    creating.value = false
  }
}
watch(createDialogVisible, async (visible) => {
  if (visible) {
    try {
      const res = await trainingApi.listModels()
      trainedModels.value = (res.data.items || []).filter((m: any) => m.status === 'completed' && m.file_path)
    } catch {
      trainedModels.value = []
    }
  }
})
function handleFileChange(uploadFile: any) {
  datasetFile.value = uploadFile.raw || null
}
async function startTask() {
  if (!selectedTaskId.value) return
  controlLoading.value = true
  try {
    await trainingApi.startTask(selectedTaskId.value)
    ElMessage.success('训练已启动')
    startPolling(selectedTaskId.value)
    await loadTaskList()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '启动训练失败')
  } finally {
    controlLoading.value = false
  }
}

async function pauseTask() {
  if (!selectedTaskId.value) return
  controlLoading.value = true
  try {
    await trainingApi.pauseTask(selectedTaskId.value)
    ElMessage.success('训练将在完成当前 epoch 后暂停')
    await loadTaskList()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '暂停失败')
  } finally {
    controlLoading.value = false
  }
}

async function resumeTask() {
  if (!selectedTaskId.value) return
  controlLoading.value = true
  try {
    await trainingApi.resumeTask(selectedTaskId.value)
    ElMessage.success('训练已恢复')
    startPolling(selectedTaskId.value)
    await loadTaskList()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '恢复失败')
  } finally {
    controlLoading.value = false
  }
}

function confirmStop() {
  stopDialogVisible.value = true
}

async function stopTask() {
  if (!selectedTaskId.value) return
  controlLoading.value = true
  stopDialogVisible.value = false
  try {
    await trainingApi.stopTask(selectedTaskId.value)
    ElMessage.success('训练已停止')
    stopPolling()
    await loadTaskList()
    await loadMetrics(selectedTaskId.value)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '停止失败')
  } finally {
    controlLoading.value = false
  }
}

function confirmDelete() {
  deleteDialogVisible.value = true
}

async function deleteTask() {
  if (!selectedTaskId.value) return
  controlLoading.value = true
  deleteDialogVisible.value = false
  try {
    await trainingApi.deleteTask(selectedTaskId.value)
    ElMessage.success('训练任务已删除')
    stopPolling()
    selectedTaskId.value = null
    logLines.value = []
    metricsData.value = []
    await loadTaskList()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '删除失败')
  } finally {
    controlLoading.value = false
  }
}

// ── 轮询 ─────────────────────────────────────────────────────────

function startPolling(taskId: string) {
  stopPolling()
  pollTimer.value = window.setInterval(async () => {
    try {
      await loadMetrics(taskId)
    } catch {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer.value !== null) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

// ── 生命周期 ─────────────────────────────────────────────────────

onMounted(async () => {
  await refreshTaskList()
})

onUnmounted(() => {
  stopPolling()
})

function startLogDrag(e: MouseEvent) {
  logDragging.value = true
  document.body.style.cursor = 'row-resize'
  logDragStartY = e.clientY
  logDragStartHeight = logHeight.value
  document.addEventListener('mousemove', onLogDrag)
  document.addEventListener('mouseup', stopLogDrag)
}

function onLogDrag(e: MouseEvent) {
  if (!logDragging.value) return
  const delta = logDragStartY - e.clientY
  logHeight.value = Math.max(60, Math.min(500, logDragStartHeight + delta))
}

function stopLogDrag() {
  logDragging.value = false
  document.body.style.cursor = ''
  logDragStartHeight = logHeight.value
  document.removeEventListener('mousemove', onLogDrag)
  document.removeEventListener('mouseup', stopLogDrag)
}

watch(logLines, () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}, { flush: 'post' })
</script>

<style scoped>
.v-chart {
  min-height: 300px;
}
</style>
