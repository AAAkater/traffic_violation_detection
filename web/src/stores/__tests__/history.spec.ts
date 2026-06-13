import { useHistoryStore } from '../history'
import * as historyApi from '@/api/history'
import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/api/history', () => ({
  getHistory: vi.fn(),
}))

describe('useHistoryStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  const mockPage = {
    items: [
      {
        image_id: 'img1',
        filename: 'test.jpg',
        created_at: '2026-01-01',
        detections: [],
      },
    ],
    total: 100,
    page: 1,
    page_size: 10,
    total_pages: 10,
  }

  it('initializes with empty state', () => {
    const store = useHistoryStore()
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.isLoading).toBe(false)
  })

  it('fetches history and updates state', async () => {
    vi.mocked(historyApi.getHistory).mockResolvedValue(mockPage)

    const store = useHistoryStore()
    await store.fetchHistory({ page: 1, page_size: 10 })

    expect(store.items).toEqual(mockPage.items)
    expect(store.total).toBe(100)
    expect(store.page).toBe(1)
    expect(store.pageSize).toBe(10)
    expect(store.totalPages).toBe(10)
    expect(store.isLoading).toBe(false)
  })

  it('sets isLoading during fetch', async () => {
    vi.mocked(historyApi.getHistory).mockResolvedValue(mockPage)

    const store = useHistoryStore()
    const promise = store.fetchHistory()
    expect(store.isLoading).toBe(true)
    await promise
    expect(store.isLoading).toBe(false)
  })
})
