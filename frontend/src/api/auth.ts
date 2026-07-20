import request from '@/utils/request'
import type { LoginParams, RegisterParams, UpdateProfileParams, ChangePasswordParams, CaptchaResponse } from '@/types/auth'

export type { LoginParams, RegisterParams, UpdateProfileParams, ChangePasswordParams, CaptchaResponse }

export const authApi = {
  getCaptcha() {
    return request.get<CaptchaResponse>('/auth/captcha')
  },
  login(data: LoginParams) {
    return request.post('/auth/login', data)
  },
  register(data: RegisterParams) {
    return request.post('/auth/register', data)
  },
  getMe() {
    return request.get('/auth/me')
  },
  // 以下为预留接口，后端尚未实现，接口就绪后设置页修改功能即可生效
  updateProfile(data: UpdateProfileParams) {
    return request.patch('/auth/me', data)
  },
  changePassword(data: ChangePasswordParams, config?: any) {
    return request.post('/auth/change-password', data, config)
  },
  uploadAvatar(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
