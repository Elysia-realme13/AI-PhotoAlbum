<template>
  <div class="h-full flex flex-col space-y-4">
    <h2 class="text-xl font-bold text-gray-800">数据集管理</h2>
    <el-tabs v-model="activeTab" type="border-card" class="flex-1 flex flex-col">
      <el-tab-pane label="数据集管理" name="datasets">
        <div class="flex items-center justify-between mb-4">
          <span class="text-sm text-gray-500">共 {{ datasetList.length }} 个数据集</span>
          <el-upload :auto-upload="false" :show-file-list="false" accept=".zip,.tar,.tar.gz,.tgz,.tar.bz2,.7z,.rar" :on-change="onDatasetUpload">
            <el-button type="primary" size="small">
              <el-icon><Upload /></el-icon> 上传数据集 ZIP
            </el-button>
          </el-upload>
        </div>
        <el-table :data="datasetList" stripe v-loading="loading.datasets" style="width: 100%">
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column prop="image_count" label="图片数" width="80" align="center" />
          <el-table-column prop="class_count" label="类别数" width="80" align="center" />
          <el-table-column label="大小" width="90" align="center">
            <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="previewDataset(row)">预览</el-button>
              <el-popconfirm title="确定删除此数据集？" @confirm="handleDeleteDataset(row)">
                <template #reference><el-button link type="danger" size="small">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="训练记录" name="records">
        <div class="flex items-center mb-4">
          <span class="text-sm text-gray-500">共 {{ taskList.length }} 条记录</span>
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px; margin-left: 12px" @change="loadTaskList">
            <el-option label="全部" value="" />
            <el-option label="进行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已暂停" value="paused" />
          </el-select>
        </div>
        <el-table :data="taskList" stripe v-loading="loading.tasks" style="width: 100%">
          <el-table-column prop="task_name" label="任务名称" min-width="160" />
          <el-table-column prop="model_name" label="模型名称" min-width="140" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="100" align="center">
            <template #default="{ row }">{{ row.current_epoch }}/{{ row.total_epochs }}</template>
          </el-table-column>
          <el-table-column prop="best_metric" label="mAP50" width="100" align="center">
            <template #default="{ row }">{{ row.best_metric !== null ? row.best_metric.toFixed(4) : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-popconfirm title="确定删除此训练记录？" @confirm="handleDeleteTask(row)">
                <template #reference><el-button link type="danger" size="small">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="磁盘空间" name="storage">
        <div class="max-w-2xl mx-auto pt-4 space-y-6">
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <div class="text-sm text-blue-600 mb-1">模型文件</div>
              <div class="text-2xl font-bold text-blue-700">{{ storageInfo.models_size_display || '-' }}</div>
            </div>
            <div class="bg-green-50 rounded-lg p-4 border border-green-200">
              <div class="text-sm text-green-600 mb-1">数据集</div>
              <div class="text-2xl font-bold text-green-700">{{ storageInfo.datasets_size_display || '-' }}</div>
            </div>
            <div class="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
              <div class="text-sm text-yellow-600 mb-1">日志文件</div>
              <div class="text-2xl font-bold text-yellow-700">{{ storageInfo.logs_size_display || '-' }}</div>
            </div>
            <div class="bg-purple-50 rounded-lg p-4 border border-purple-200">
              <div class="text-sm text-purple-600 mb-1">总计</div>
              <div class="text-2xl font-bold text-purple-700">{{ storageInfo.total_size_display || '-' }}</div>
            </div>
          </div>
          <div class="bg-white rounded-lg border p-4">
            <h4 class="text-sm font-semibold text-gray-700 mb-3">空间清理</h4>
            <p class="text-sm text-gray-500 mb-4">清理失败训练任务产生的临时文件，释放磁盘空间。</p>
            <el-button type="warning" @click="handleCleanStorage" :loading="cleaning">
              <el-icon><Delete /></el-icon> 清理临时文件
            </el-button>
            <span v-if="cleanResult" class="ml-3 text-sm text-green-600">
              已清理 {{ cleanResult.cleaned_count }} 个文件，释放 {{ cleanResult.cleaned_size_display }}
            </span>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import trainingApi, { type DatasetItem, type TrainingTask, type StorageInfo } from '@/api/training'

const activeTab = ref('datasets')
const datasetList = ref<DatasetItem[]>([])
const taskList = ref<TrainingTask[]>([])
const filterStatus = ref('')
const storageInfo = ref<StorageInfo>({
  models_size: 0, datasets_size: 0, logs_size: 0, total_size: 0,
  models_size_display: '0 B', datasets_size_display: '0 B',
  logs_size_display: '0 B', total_size_display: '0 B',
})
const cleaning = ref(false)
const cleanResult = ref<any>(null)
const loading = reactive({ datasets: false, tasks: false })

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(2) + ' MB'
}
function statusType(status: string) {
  const m: Record<string, string> = { pending: 'info', running: 'warning', paused: '', completed: 'success', failed: 'danger' }
  return m[status] || 'info'
}
function statusLabel(status: string) {
  const m: Record<string, string> = { pending: '待开始', running: '进行中', paused: '已暂停', completed: '已完成', failed: '失败' }
  return m[status] || status
}
async function loadDatasets() {
  loading.datasets = true
  try { const r = await trainingApi.listDatasets(); datasetList.value = r.data.items }
  catch { ElMessage.error('加载数据集列表失败') }
  finally { loading.datasets = false }
}
async function loadTaskList() {
  loading.tasks = true
  try { const r = await trainingApi.listTasks(filterStatus.value || undefined); taskList.value = r.data.items }
  catch { ElMessage.error('加载训练记录失败') }
  finally { loading.tasks = false }
}
async function loadStorageInfo() {
  try { const r = await trainingApi.getStorageInfo(); storageInfo.value = r.data }
  catch { /* ignore */ }
}
async function onDatasetUpload(f: any) {
  if (!f.raw) return
  const fileName = f.raw.name
  const lower = fileName.toLowerCase()
  const stem = lower.endsWith(".tar.gz") || lower.endsWith(".tgz") ? fileName.slice(0, -7)
    : lower.endsWith(".tar.bz2") ? fileName.slice(0, -8)
    : (fileName.lastIndexOf(".") > 0 ? fileName.slice(0, fileName.lastIndexOf(".")) : fileName)
  if (datasetList.value.some(ds => ds.name === stem)) {
    ElMessage.warning(`数据集 "${stem}" 已存在，请勿重复上传`)
    return
}
  const uploadMsg = ElMessage({ message: '正在上传数据集，请稍候...', duration: 0 })
  try {
    await trainingApi.uploadDataset(f.raw)
    uploadMsg.close()
    ElMessage.success('上传成功')
    await loadDatasets()
  } catch (e: any) {
    uploadMsg.close()
    ElMessage.error(e.response?.data?.detail || '上传失败')
  }
}
async function previewDataset(ds: DatasetItem) {
  try { const r = await trainingApi.previewDataset(ds.id); console.log('数据集预览:', r.data) }
  catch { ElMessage.error('加载预览失败') }
}
async function handleDeleteDataset(ds: DatasetItem) {
  try { await trainingApi.deleteDataset(ds.id); ElMessage.success('数据集已删除'); await loadDatasets() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '删除失败') }
}
async function handleDeleteTask(t: TrainingTask) {
  try { await trainingApi.deleteTask(t.id); ElMessage.success('训练记录已删除'); await loadTaskList() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '删除失败') }
}
async function handleCleanStorage() {
  cleaning.value = true
  try { const r = await trainingApi.cleanStorage(); cleanResult.value = r.data; ElMessage.success('清理完成'); await loadStorageInfo() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '清理失败') }
  finally { cleaning.value = false }
}
onMounted(async () => { await Promise.all([loadDatasets(), loadTaskList(), loadStorageInfo()]) })
</script>
