import { apiClient } from './client'
import type { PromptData, PromptListItem } from '@/types/api'

export function getActivePrompt(): Promise<PromptData> {
  return apiClient.get<PromptData>('/v1/prompt').then((res) => res.data)
}

export function setPrompt(name: string, content: string): Promise<PromptData> {
  return apiClient
    .post<PromptData>('/v1/prompt', null, {
      params: { name, content },
    })
    .then((res) => res.data)
}

export function listPrompts(): Promise<PromptListItem[]> {
  return apiClient.get<PromptListItem[]>('/v1/prompt/list').then((res) => res.data)
}
