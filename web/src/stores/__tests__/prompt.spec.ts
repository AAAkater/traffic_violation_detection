import { usePromptStore } from '../prompt'
import * as promptApi from '@/api/prompt'
import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/api/prompt', () => ({
  getActivePrompt: vi.fn(),
  setPrompt: vi.fn(),
  listPrompts: vi.fn(),
}))

describe('usePromptStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with empty state', () => {
    const store = usePromptStore()
    expect(store.currentPrompt).toBeNull()
    expect(store.promptList).toEqual([])
  })

  it('fetches active prompt', async () => {
    const mockData = { name: 'test', content: 'You are a judge' }
    vi.mocked(promptApi.getActivePrompt).mockResolvedValue(mockData)

    const store = usePromptStore()
    await store.fetchActive()

    expect(store.currentPrompt).toEqual(mockData)
  })

  it('fetches prompt list', async () => {
    const mockList = [{ name: 'p1', content: '...', is_active: true, updated_at: '2026-01-01' }]
    vi.mocked(promptApi.listPrompts).mockResolvedValue(mockList)

    const store = usePromptStore()
    await store.fetchList()

    expect(store.promptList).toEqual(mockList)
  })

  it('sets a new prompt', async () => {
    const mockData = { name: 'new', content: 'Be fair' }
    vi.mocked(promptApi.setPrompt).mockResolvedValue(mockData)

    const store = usePromptStore()
    const result = await store.set('new', 'Be fair')

    expect(result).toEqual(mockData)
    expect(store.currentPrompt).toEqual(mockData)
  })
})
