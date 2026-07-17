import request from '@/utils/request'
import type { FaceCluster } from '@/types/face'
import type { PhotoItem } from '@/types/photo'

export const faceApi = {
  /** 获取所有人物聚类（含已命名和未命名） */
  listIdentities() {
    return request.get<FaceCluster[]>('/faces/identities')
  },

  /** 获取某人物聚类下的所有照片 */
  identityPhotos(id: string) {
    return request.get<PhotoItem[]>(`/faces/identities/${id}/photos`)
  },

  /** 命名/重命名聚类 */
  renameCluster(clusterId: string, name: string) {
    return request.post('/faces/identities/name', { cluster_id: clusterId, name })
  },

  /** 合并两个聚类 */
  mergeClusters(sourceClusterId: string, targetClusterId: string) {
    return request.post('/faces/identities/merge', {
      source_ids: [sourceClusterId],
      target_id: targetClusterId,
    })
  },

  /** 批量合并多个聚类到目标聚类 */
  mergeClustersBatch(sourceClusterIds: string[], targetClusterId: string) {
    return request.post('/faces/identities/merge', {
      source_ids: sourceClusterIds,
      target_id: targetClusterId,
    })
  },
}
