export interface FaceIdentity {
  id: string
  owner_id: string
  identity_name: string
  description?: string | null
  default_face_id?: number | null
  is_hidden: boolean
  face_count: number
  created_at: string
  cover_photo_id?: string // 前端封面用，取该人物代表照片
}

export interface FaceIdentityUpdate {
  identity_name?: string
  description?: string
  is_hidden?: boolean
}

export interface FaceItem {
  id: number
  photo_id: string
  face_identity_id?: string | null
  face_rect?: number[] | null
  confidence?: number | null
}
