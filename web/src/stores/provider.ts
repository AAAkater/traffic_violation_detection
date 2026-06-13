import {
  listProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  listProviderModels,
  listActivatedModels,
  activateModel,
  deactivateModel,
} from '@/api/provider'
import type { ProviderData, ProviderCreate, ProviderUpdate, ProviderModelsData } from '@/types/api'
import { defineStore } from 'pinia'
import { shallowRef } from 'vue'

export const useProviderStore = defineStore('provider', () => {
  const providers = shallowRef<ProviderData[]>([])
  const currentModels = shallowRef<ProviderModelsData | null>(null)
  const activatedModels = shallowRef<string[]>([])
  const isLoading = shallowRef(false)

  async function fetchAll() {
    isLoading.value = true
    try {
      providers.value = await listProviders()
    } finally {
      isLoading.value = false
    }
  }

  async function create(data: ProviderCreate) {
    const provider = await createProvider(data)
    providers.value = [...providers.value, provider]
    return provider
  }

  async function update(providerId: number, data: ProviderUpdate) {
    const updated = await updateProvider(providerId, data)
    providers.value = providers.value.map((p) => (p.id === providerId ? updated : p))
    return updated
  }

  async function remove(providerId: number) {
    await deleteProvider(providerId)
    providers.value = providers.value.filter((p) => p.id !== providerId)
  }

  async function fetchModels(providerId: number) {
    currentModels.value = await listProviderModels(providerId)
    return currentModels.value
  }

  async function fetchActivatedModels(providerId: number) {
    activatedModels.value = await listActivatedModels(providerId)
    return activatedModels.value
  }

  async function activateModelAction(providerId: number, model: string) {
    const updated = await activateModel(providerId, model)
    providers.value = providers.value.map((p) => (p.id === providerId ? updated : p))
    return updated
  }

  async function deactivateModelAction(providerId: number, model: string) {
    const updated = await deactivateModel(providerId, model)
    providers.value = providers.value.map((p) => (p.id === providerId ? updated : p))
    return updated
  }

  return {
    providers,
    currentModels,
    activatedModels,
    isLoading,
    fetchAll,
    create,
    update,
    remove,
    fetchModels,
    fetchActivatedModels,
    activateModel: activateModelAction,
    deactivateModel: deactivateModelAction,
  }
})
