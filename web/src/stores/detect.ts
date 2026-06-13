import { uploadImage } from '@/api/detect'
import type { DetectData } from '@/types/api'
import { defineStore } from 'pinia'
import { shallowRef } from 'vue'

export const useDetectStore = defineStore('detect', () => {
  const currentResult = shallowRef<DetectData | null>(null)
  const isUploading = shallowRef(false)
  const error = shallowRef<string | null>(null)

  async function upload(file: File) {
    isUploading.value = true
    error.value = null
    try {
      currentResult.value = await uploadImage(file)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '上传失败'
      throw e
    } finally {
      isUploading.value = false
    }
  }

  function reset() {
    currentResult.value = null
    error.value = null
  }

  return { currentResult, isUploading, error, upload, reset }
})
