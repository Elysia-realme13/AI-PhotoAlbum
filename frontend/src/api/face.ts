import request from '@/utils/request'
import type { FaceIdentity, FaceIdentityUpdate } from '@/types/face'
import type { PhotoItem } from '@/types/photo'

// 后端 api/face.py 尚为 stub，list 类接口用 silent 静默失败，由页面 mock 兜底
export const faceApi = {
  listIdentities: () => request.get<FaceIdentity[]>('/faces/identities', { silent: true }),
  identityPhotos: (id: string) =>
    request.get<PhotoItem[]>(`/faces/identities/${id}/photos`, { silent: true }),
  updateIdentity: (id: string, data: FaceIdentityUpdate) =>
    request.put(`/faces/identities/${id}`, data),
  mergeIdentities: (source_ids: string[], target_id: string) =>
    request.post('/faces/identities/merge', { source_ids, target_id }),
}
