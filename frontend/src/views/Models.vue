<template>
  <div class="h-full flex flex-col space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <h2 class="text-xl font-bold text-gray-800">模型管理</h2>
        <el-tag v-if="defaultModel" type="success" effect="plain" size="small">
          当前默认: {{ defaultModel }}
        </el-tag>
      </div>
      <div class="flex items-center space-x-3">
        <el-button type="primary" @click="importDialogVisible = true">
          <el-icon><Upload /></el-icon> 导入模型
        </el-button>
        <el-button @click="loadModels">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto">
      <el-table :data="modelList" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="model_name" label="模型名称" min-width="140" />
        <el-table-column prop="task_name" label="任务名称" min-width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'danger'" size="small">
              {{ row.status === 'completed' ? '已完成' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mAP50" label="mAP50" width="90" align="center">
          <template #default="{ row }">
            {{ row.mAP50 !== null ? row.mAP50.toFixed(4) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="mAP50_95" label="mAP50-95" width="100" align="center">
          <template #default="{ row }">
            {{ row.mAP50_95 !== null ? row.mAP50_95.toFixed(4) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="class_count" label="类别数" width="70" align="center" />
        <el-table-column label="文件大小" width="100" align="center">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="默认" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" size="small" effect="dark">&#10003;</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="handleExport(row, 'pt')">导出pt</el-button>
            <el-button link type="primary" size="small" @click="handleExport(row, 'onnx')">导出ONNX</el-button>
            <el-button v-if="!row.is_default" link type="success" size="small" @click="handleSetDefault(row)">设为默认</el-button>
            <el-popconfirm title="确定删除此模型？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import trainingApi, { type ModelInfo, type MetricItem } from '@/api/training'
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])
const loading = ref(false)
const modelList = ref<ModelInfo[]>([])
const defaultModel = ref<string | null>(null)
const importDialogVisible = ref(false)
const importModelName = ref('')
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const detailVisible = ref(false)
const detailData = ref<any>(null)
const detailMetrics = ref<MetricItem[]>([])
function formatSize(bytes: number | null) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(2) + ' MB'
}
function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return h + 'h ' + m + 'm'
  if (m > 0) return m + 'm ' + s + 's'
  return s + 's'
}
async function loadModels() {
  loading.value = true
  try {
    const [modelsRes, defaultRes] = await Promise.all([
      trainingApi.listModels(),
      trainingApi.getDefaultModel().catch(() => ({ data: { model_name: null } })),
    ])
    modelList.value = modelsRes.data.items
    defaultModel.value = defaultRes.data.model_name
  } catch {
    ElMessage.error('加载模型列表失败')
  } finally {
    loading.value = false
  }
}
async function handleExport(model: ModelInfo, format: 'pt' | 'onnx') {
  try {
    const res = await trainingApi.exportModel(model.model_name, format)
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = model.model_name + '.' + format
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(format.toUpperCase() + ' 导出成功')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '导出失败')
  }
}
async function handleSetDefault(model: ModelInfo) {
  try {
    await trainingApi.setDefaultModel(model.model_name)
    ElMessage.success('已设为默认模型: ' + model.model_name)
    await loadModels()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '设置失败')
  }
}
async function handleDelete(model: ModelInfo) {
  try {
    await trainingApi.deleteModel(model.model_name)
    ElMessage.success('模型 ' + model.model_name + ' 已删除')
    await loadModels()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '删除失败')
  }
}
function onImportFileChange(uploadFile: any) {
  importFile.value = uploadFile.raw
}
async function handleImport() {
  if (!importModelName.value.trim()) { ElMessage.warning('请输入模型名称'); return }
  if (!importFile.value) { ElMessage.warning('请选择模型文件'); return }
  importLoading.value = true
  try {
    await trainingApi.importModel(importFile.value, importModelName.value)
    ElMessage.success('模型导入成功')
    importDialogVisible.value = false
    importModelName.value = ''
    importFile.value = null
    await loadModels()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '导入失败')
  } finally {
    importLoading.value = false
  }
}
async function showDetail(model: ModelInfo) {
  try {
    const res = await trainingApi.getModelDetail(model.model_name)
    detailData.value = res.data
    detailMetrics.value = res.data.metrics || []
    detailVisible.value = true
  } catch {
    ElMessage.error('加载模型详情失败')
  }
}
onMounted(() => { loadModels() })
</script>
