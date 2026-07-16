export interface FaceCluster {
  identity_id: string
  identity_name: string | null
  face_count: number
  cover_photo_id: string | null
}

export interface FaceIdentity {
  id: string
  owner_id: string
  identity_name: string
  description?: string | null
  default_face_id?: number | null
  is_hidden: boolean
  face_count: number
  created_at: string
  cover_photo_id?: string
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
