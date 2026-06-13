import { apiClient } from './client'
import type {
  ProviderCreate,
  ProviderData,
  ProviderModelsData,
  ProviderUpdate,
  ModelActivateRequest,
  ModelDeactivateRequest,
} from '@/types/api'

export function listProviders(): Promise<ProviderData[]> {
  return apiClient.get<ProviderData[]>('/v1/provider/list').then((res) => res.data)
}

export function getProvider(id: number): Promise<ProviderData> {
  return apiClient.get<ProviderData>(`/v1/provider/${id}`).then((res) => res.data)
}

export function createProvider(data: ProviderCreate): Promise<ProviderData> {
  return apiClient.post<ProviderData>('/v1/provider', data).then((res) => res.data)
}

export function updateProvider(providerId: number, data: ProviderUpdate): Promise<ProviderData> {
  return apiClient
    .post<ProviderData>('/v1/provider/update', data, {
      params: { provider_id: providerId },
    })
    .then((res) => res.data)
}

export function deleteProvider(providerId: number): Promise<Record<string, unknown>> {
  return apiClient
    .post<Record<string, unknown>>('/v1/provider/delete', null, {
      params: { provider_id: providerId },
    })
    .then((res) => res.data)
}

export function listProviderModels(providerId: number): Promise<ProviderModelsData> {
  return apiClient
    .get<ProviderModelsData>(`/v1/provider/${providerId}/models`)
    .then((res) => res.data)
}

export function listActivatedModels(providerId: number): Promise<string[]> {
  return apiClient
    .get<string[]>(`/v1/provider/${providerId}/activated-models`)
    .then((res) => res.data)
}

export function activateModel(providerId: number, model: string): Promise<ProviderData> {
  const body: ModelActivateRequest = { model }
  return apiClient
    .post<ProviderData>(`/v1/provider/${providerId}/activate-model`, body)
    .then((res) => res.data)
}

export function deactivateModel(providerId: number, model: string): Promise<ProviderData> {
  const body: ModelDeactivateRequest = { model }
  return apiClient
    .post<ProviderData>(`/v1/provider/${providerId}/deactivate-model`, body)
    .then((res) => res.data)
}
