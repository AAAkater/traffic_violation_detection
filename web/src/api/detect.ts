import { apiClient } from './client'
import type { DetectData } from '@/types/api'

export function uploadImage(imageFile: File): Promise<DetectData> {
  const formData = new FormData()
  formData.append('image_file', imageFile)

  return apiClient
    .post<DetectData>('/v1/detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((res) => res.data)
}
