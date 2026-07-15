import request from '@/utils/request'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  email: string
  password: string
  nickname?: string
}

export interface UpdateProfileParams {
  nickname?: string
  avatar_url?: string
}

export interface ChangePasswordParams {
  old_password: string
  new_password: string
}

export const authApi = {
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
  changePassword(data: ChangePasswordParams) {
    return request.post('/auth/change-password', data)
  },
}
