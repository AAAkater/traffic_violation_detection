import { apiClient } from './client'
import type { HistoryPage } from '@/types/api'

export function getHistory(params?: { page?: number; page_size?: number }): Promise<HistoryPage> {
  return apiClient.get<HistoryPage>('/v1/history', { params }).then((res) => res.data)
}
