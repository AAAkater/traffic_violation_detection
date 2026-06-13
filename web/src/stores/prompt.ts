import { getActivePrompt, setPrompt, listPrompts } from '@/api/prompt'
import type { PromptData, PromptListItem } from '@/types/api'
import { defineStore } from 'pinia'
import { shallowRef } from 'vue'

export const usePromptStore = defineStore('prompt', () => {
  const currentPrompt = shallowRef<PromptData | null>(null)
  const promptList = shallowRef<PromptListItem[]>([])
  const isLoading = shallowRef(false)

  async function fetchActive() {
    isLoading.value = true
    try {
      currentPrompt.value = await getActivePrompt()
    } finally {
      isLoading.value = false
    }
  }

  async function fetchList() {
    isLoading.value = true
    try {
      promptList.value = await listPrompts()
    } finally {
      isLoading.value = false
    }
  }

  async function set(name: string, content: string) {
    const prompt = await setPrompt(name, content)
    currentPrompt.value = prompt
    return prompt
  }

  return { currentPrompt, promptList, isLoading, fetchActive, fetchList, set }
})
