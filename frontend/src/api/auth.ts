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
}
