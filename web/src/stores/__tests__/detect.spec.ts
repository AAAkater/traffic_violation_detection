import { useDetectStore } from '../detect'
import * as detectApi from '@/api/detect'
import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/api/detect', () => ({
  uploadImage: vi.fn(),
}))

describe('useDetectStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with null result', () => {
    const store = useDetectStore()
    expect(store.currentResult).toBeNull()
    expect(store.isUploading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('sets uploading state during upload', async () => {
    const mockResult = { image_id: 'abc123', detections: [] }
    vi.mocked(detectApi.uploadImage).mockResolvedValue(mockResult)

    const store = useDetectStore()
    const file = new File([''], 'test.jpg', { type: 'image/jpeg' })

    const promise = store.upload(file)
    expect(store.isUploading).toBe(true)

    await promise
    expect(store.isUploading).toBe(false)
    expect(store.currentResult).toEqual(mockResult)
  })

  it('handles upload error', async () => {
    vi.mocked(detectApi.uploadImage).mockRejectedValue(new Error('Network error'))

    const store = useDetectStore()
    const file = new File([''], 'test.jpg', { type: 'image/jpeg' })

    await expect(store.upload(file)).rejects.toThrow('Network error')
    expect(store.isUploading).toBe(false)
    expect(store.error).toBe('Network error')
  })

  it('resets state', () => {
    const store = useDetectStore()
    store.currentResult = { image_id: 'abc', detections: [] }
    store.error = 'some error'

    store.reset()
    expect(store.currentResult).toBeNull()
    expect(store.error).toBeNull()
  })
})
