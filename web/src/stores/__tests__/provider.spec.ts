import { useProviderStore } from '../provider'
import * as providerApi from '@/api/provider'
import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/api/provider', () => ({
  listProviders: vi.fn(),
  createProvider: vi.fn(),
  updateProvider: vi.fn(),
  deleteProvider: vi.fn(),
  listProviderModels: vi.fn(),
  listActivatedModels: vi.fn(),
  activateModel: vi.fn(),
  deactivateModel: vi.fn(),
}))

describe('useProviderStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  const mockProvider = {
    id: 1,
    name: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    api_key: 'sk-***',
    activated_models: [],
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  }

  it('initializes with empty state', () => {
    const store = useProviderStore()
    expect(store.providers).toEqual([])
    expect(store.currentModels).toBeNull()
  })

  it('fetches all providers', async () => {
    vi.mocked(providerApi.listProviders).mockResolvedValue([mockProvider])

    const store = useProviderStore()
    await store.fetchAll()

    expect(store.providers).toEqual([mockProvider])
  })

  it('creates a provider', async () => {
    vi.mocked(providerApi.createProvider).mockResolvedValue(mockProvider)

    const store = useProviderStore()
    const result = await store.create({
      name: 'OpenAI',
      base_url: 'https://api.openai.com/v1',
      api_key: 'sk-xxx',
    })

    expect(result).toEqual(mockProvider)
    expect(store.providers).toContainEqual(mockProvider)
  })

  it('removes a provider', async () => {
    const store = useProviderStore()
    vi.mocked(providerApi.deleteProvider).mockResolvedValue({})
    store.providers = [mockProvider, { ...mockProvider, id: 2 }]

    await store.remove(1)

    expect(store.providers).toHaveLength(1)
    expect(store.providers[0]!.id).toBe(2)
  })
})
