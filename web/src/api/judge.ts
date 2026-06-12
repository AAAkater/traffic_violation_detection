import { apiClient } from './client'
import type { JudgeData } from '@/types/api'

export function judge(params: {
  image_id: string
  provider_id: number
  model: string
}): Promise<JudgeData> {
  return apiClient.post<JudgeData>('/v1/judge', null, { params }).then((res) => res.data)
}
