/**
 * 训练与管理模块的 API 封装
 *
 * 提供训练任务、数据集、模型管理的所有 API 调用
 */
import request from '@/utils/request'

export interface TrainingConfig {
  pretrained_model: string
  imgsz: number
  epochs: number
  batch: number
  lr0: number
  optimizer: string
  momentum: number
  weight_decay: number
  warmup_epochs: number
  multi_scale: boolean
  mixup: number
  mosaic: number
  copy_paste: number
  device: string
  workers: number
  seed: number
  save_period: number
  patience: number
  val_split: number
  use_dataset_split: boolean
}

export interface CreateTaskParams {
  task_name: string
  model_name: string
  description?: string
  dataset_id?: string
  config: TrainingConfig
}

export interface TrainingTask {
  id: string
  task_name: string
  model_name: string
  description: string | null
  dataset_id: string | null
  dataset_name: string | null
  status: string
  config: Record<string, any>
  current_epoch: number
  total_epochs: number
  best_metric: number | null
  checkpoint_path: string | null
  model_path: string | null
  log_path: string | null
  created_at: string | null
  updated_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface MetricItem {
  id: string
  task_id: string
  epoch: number
  metrics: Record<string, number>
  created_at: string | null
}

export interface ModelInfo {
  id: string
  model_name: string
  task_name: string
  status: string
  file_size: number | null
  file_path: string | null
  best_metric: number | null
  mAP50: number | null
  mAP50_95: number | null
  recall: number | null
  precision: number | null
  class_count: number | null
  dataset_name: string | null
  config: Record<string, any> | null
  is_default: boolean
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
}

export interface DatasetItem {
  id: string
  name: string
  path: string
  image_count: number
  class_names: string[]
  class_count: number
  file_size: number
  created_at: string | null
}

export interface DatasetPreview {
  id: string
  name: string
  class_names: string[]
  sample_images: string[]
  image_count: number
  sample_image_urls: string[]
}

export interface StorageInfo {
  models_size: number
  datasets_size: number
  logs_size: number
  total_size: number
  models_size_display: string
  datasets_size_display: string
  logs_size_display: string
  total_size_display: string
}

export const trainingApi = {
  // --- 训练任务 ---

  /** 创建训练任务 */
  createTask(data: CreateTaskParams) {
    return request.post<TrainingTask>('/training/tasks', data)
  },

  /** 创建训练任务并同时上传数据集（multipart/form-data） */
  createTaskWithDataset(data: {
    file: File
    task_name: string
    model_name: string
    description?: string
    config: TrainingConfig
  }) {
    const formData = new FormData()
    formData.append('file', data.file)
    formData.append('task_name', data.task_name)
    formData.append('model_name', data.model_name)
    if (data.description) formData.append('description', data.description)
    formData.append('config', JSON.stringify(data.config))
    return request.post<TrainingTask>('/training/tasks/with-dataset', formData, {
      timeout: 600000,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    })
  },

  /** 获取任务列表 */
  listTasks(status?: string) {
    return request.get<{ total: number; items: TrainingTask[] }>('/training/tasks', {
      params: status ? { status } : {},
    })
  },

  /** 获取任务详情（含指标） */
  getTaskDetail(id: string) {
    return request.get<{ task: TrainingTask; metrics: MetricItem[]; logs: string[] }>(`/training/tasks/${id}`)
  },

  /** 启动训练 */
  startTask(id: string) {
    return request.post<{ message: string }>(`/training/tasks/${id}/start`)
  },

  /** 暂停训练 */
  pauseTask(id: string) {
    return request.post<{ message: string }>(`/training/tasks/${id}/pause`)
  },

  /** 恢复训练 */
  resumeTask(id: string) {
    return request.post<{ message: string }>(`/training/tasks/${id}/resume`)
  },

  /** 停止训练 */
  stopTask(id: string) {
    return request.post<{ message: string }>(`/training/tasks/${id}/stop`)
  },

  /** 删除任务 */
  deleteTask(id: string) {
    return request.delete(`/training/tasks/${id}`)
  },

  /** 获取任务状态 */
  getTaskStatus(id: string) {
    return request.get(`/training/tasks/${id}/status`)
  },

  // --- 模型管理 ---

  /** 获取模型列表 */
  listModels() {
    return request.get<{ total: number; items: ModelInfo[] }>('/models')
  },

  /** 获取模型详情 */
  getModelDetail(modelName: string) {
    return request.get(`/models/${modelName}`)
  },

  /** 导出模型 */
  exportModel(modelName: string, format: 'pt' | 'onnx') {
    return request.post(`/models/${modelName}/export`, { format }, { responseType: 'blob' })
  },

  /** 导入模型 */
  importModel(file: File, modelName: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model_name', modelName)
    return request.post('/models/import', formData)
  },

  /** 设为默认模型 */
  setDefaultModel(modelName: string) {
    return request.post(`/models/${modelName}/set-default`)
  },

  /** 获取默认模型 */
  getDefaultModel() {
    return request.get('/models/default/info')
  },
  /** 重置默认模型为 YOLOv26 */
  resetDefaultModel() {
    return request.post('/models/default/reset')
  },

  /** 删除模型 */
  deleteModel(modelName: string) {
    return request.delete(`/models/${modelName}`)
  },

  /** 更新模型信息（任务名称和描述） */
  updateModel(modelName: string, data: { task_name: string; description?: string }) {
    return request.patch(`/models/${modelName}`, data)
  },

  // --- 数据集管理 ---

  /** 上传数据集 ZIP */
  uploadDataset(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<DatasetItem>('/datasets/upload', formData, {
      timeout: 600000,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    })
  },

  /** 获取数据集列表 */
  listDatasets() {
    return request.get<{ total: number; items: DatasetItem[] }>('/datasets')
  },

  /** 预览数据集 */
  previewDataset(id: string) {
    return request.get<DatasetPreview>(`/datasets/${id}/preview`)
  },

  /** 删除数据集 */
  deleteDataset(id: string) {
    return request.delete(`/datasets/${id}`)
  },

  // --- 存储管理 ---

  /** 获取存储信息 */
  getStorageInfo() {
    return request.get<StorageInfo>('/datasets/storage/info')
  },

  /** 清理临时文件 */
  cleanStorage() {
    return request.post('/datasets/storage/clean')
  },
}

export default trainingApi
