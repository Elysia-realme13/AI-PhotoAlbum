import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'

// 扩展 Axios 请求配置：silent 为 true 时，请求失败不弹出全局错误提示
declare module 'axios' {
  export interface AxiosRequestConfig {
    silent?: boolean
  }
}

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器：添加 Token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：BaseResponse 解包 + 统一错误处理
request.interceptors.response.use(
  (response) => {
    // 后端统一返回 {code, msg, data} 格式，自动解包 data
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body && 'data' in body) {
      response.data = body.data
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      useUserStore().logout()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (error.config?.silent) {
      // 静默模式：跳过全局错误提示，由调用方自行处理
    } else if (error.response?.data?.error) {
      // 自定义异常处理器返回的 error 字段
      ElMessage.error(error.response.data.error)
    } else if (error.response?.data?.detail) {
      // FastAPI 默认错误格式（如 404、参数校验失败等）
      const detail = error.response.data.detail
      const msg = typeof detail === 'string' ? detail : JSON.stringify(detail)
      ElMessage.error(msg)
    } else if (error.response) {
      // 有响应但格式未知，显示状态码
      ElMessage.error(`请求失败 (${error.response.status})，请稍后重试`)
    } else {
      // 无响应（网络错误、CORS、服务器未启动等）
      ElMessage.error('网络错误，请检查服务器是否启动')
    }
    return Promise.reject(error)
  }
)

export default request
