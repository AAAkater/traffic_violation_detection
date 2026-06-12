import { getHistory } from '@/api/history'
import type { HistoryItem } from '@/types/api'
import { defineStore } from 'pinia'
import { shallowRef } from 'vue'

export const useHistoryStore = defineStore('history', () => {
  const items = shallowRef<HistoryItem[]>([])
  const total = shallowRef(0)
  const page = shallowRef(1)
  const pageSize = shallowRef(10)
  const totalPages = shallowRef(0)
  const isLoading = shallowRef(false)

  async function fetchHistory(params?: { page?: number; page_size?: number }) {
    isLoading.value = true
    try {
      const data = await getHistory(params)
      items.value = data.items ?? []
      total.value = data.total
      page.value = data.page
      pageSize.value = data.page_size
      totalPages.value = data.total_pages
    } finally {
      isLoading.value = false
    }
  }

  return { items, total, page, pageSize, totalPages, isLoading, fetchHistory }
})
