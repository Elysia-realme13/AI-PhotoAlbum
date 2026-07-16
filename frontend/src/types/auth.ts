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
