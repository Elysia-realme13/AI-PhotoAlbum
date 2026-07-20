export interface LoginParams {
  username: string
  password: string
  captcha_id?: string
  captcha_code?: string
}

export interface CaptchaResponse {
  captcha_id: string
  captcha_image: string
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
