import request from '@/utils/request'
import type { TaskItem, TaskStats } from '@/types/task'

export interface TaskListParams {
  page?: number
  page_size?: number
  status?: string
  task_type?: string
  photo_id?: string
}

export interface TaskListResponse {
  total: number
  page: number
  page_size: number
  items: TaskItem[]
}

export const taskApi = {
  /** 任务列表（支持按状态/类型/照片筛选） */
  list(params: TaskListParams = {}) {
    return request.get<TaskListResponse>('/tasks', { params })
  },

  /** 任务统计（各状态计数） */
  stats() {
    return request.get<TaskStats>('/tasks/stats')
  },

  /** 重试失败任务 */
  retry(id: string) {
    return request.post<TaskItem>(`/tasks/${id}/retry`)
  },

  /** 取消等待中的任务 */
  cancel(id: string) {
    return request.delete(`/tasks/${id}`)
  },

  /** 为存量照片补建反向地理编码任务（有 GPS 但城市未解析） */
  geocodeBackfill() {
    return request.post<{ created: number }>('/tasks/geocode-backfill')
  },
}
