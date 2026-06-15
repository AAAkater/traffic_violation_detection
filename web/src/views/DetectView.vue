<script setup lang="ts">
import { judge } from '@/api/judge'
import DetectionImage from '@/components/detect/DetectionImage.vue'
import DetectionList from '@/components/detect/DetectionList.vue'
import ImageUploader from '@/components/detect/ImageUploader.vue'
import { useMessage } from '@/composables/useMessage'
import { useDetectStore } from '@/stores/detect'
import { useHistoryStore } from '@/stores/history'
import { useProviderStore } from '@/stores/provider'
import type { DetectData, JudgeData, ProviderData } from '@/types/api'
import { NCard, NSteps, NStep, NButton, NSelect, NSpace } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { shallowRef, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const detectStore = useDetectStore()
const providerStore = useProviderStore()
const historyStore = useHistoryStore()
const { showError } = useMessage()
const { currentResult, isUploading } = storeToRefs(detectStore)

const currentStep = shallowRef(1)
const judgeResult = shallowRef<JudgeData | null>(null)
const uploadedImageUrl = shallowRef<string | null>(null)

const providers = shallowRef<ProviderData[]>([])
const selectedProviderId = shallowRef<number | null>(null)
const selectedModel = shallowRef<string | null>(null)
const availableModels = shallowRef<string[]>([])
const isJudging = shallowRef(false)

onMounted(async () => {
  try {
    await providerStore.fetchAll()
    providers.value = providerStore.providers
  } catch {
    showError('获取提供商列表失败')
  }

  const targetImageId = route.query.image_id as string | undefined
  if (targetImageId) {
    let historyItem = historyStore.items.find((i) => i.image_id === targetImageId)
    if (!historyItem) {
      await historyStore.fetchHistory({ page: 1, page_size: 100 })
      historyItem = historyStore.items.find((i) => i.image_id === targetImageId)
    }
    if (historyItem) {
      detectStore.setResult({
        image_id: historyItem.image_id,
        detections: historyItem.detections as DetectData['detections'],
      })
      if (historyItem.image_url) {
        uploadedImageUrl.value = historyItem.image_url
      }
      currentStep.value = 2
    }
  }
})

watch(selectedProviderId, async (id, oldId) => {
  if (id === null) return
  try {
    const models = await providerStore.fetchActivatedModels(id)
    availableModels.value = models
    // Only reset model if provider changed
    if (id !== oldId) {
      selectedModel.value = null
    }
  } catch {
    showError('获取模型列表失败')
  }
})

async function handleUpload(file: File) {
  if (uploadedImageUrl.value) {
    URL.revokeObjectURL(uploadedImageUrl.value)
  }
  uploadedImageUrl.value = URL.createObjectURL(file)
  await detectStore.upload(file)
  // Restore available models if a provider was previously selected
  if (selectedProviderId.value !== null && availableModels.value.length === 0) {
    try {
      const models = await providerStore.fetchActivatedModels(selectedProviderId.value)
      availableModels.value = models
    } catch {
      // ignore
    }
  }
  currentStep.value = 2
}

async function handleJudge() {
  if (!selectedProviderId.value || !selectedModel.value || !currentResult.value) return
  isJudging.value = true
  try {
    const result = await judge({
      image_id: currentResult.value.image_id,
      provider_id: selectedProviderId.value,
      model: selectedModel.value,
    })
    judgeResult.value = result
    currentStep.value = 3
  } catch (e) {
    showError(e instanceof Error ? e.message : '判定失败')
  } finally {
    isJudging.value = false
  }
}

function handleReset() {
  if (uploadedImageUrl.value) {
    URL.revokeObjectURL(uploadedImageUrl.value)
    uploadedImageUrl.value = null
  }
  detectStore.reset()
  judgeResult.value = null
  currentStep.value = 1
}
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <h1 class="text-3xl font-bold text-gray-800 dark:text-white">交通违规检测</h1>

    <NCard>
      <NSteps :current="currentStep" class="mb-8">
        <NStep title="上传图片" description="上传交通现场图片" />
        <NStep title="YOLO 检测" description="AI 自动识别交通信号灯" />
        <NStep title="LLM 判定" description="AI 大模型判定是否违规" />
      </NSteps>

      <!-- Step 1: Upload -->
      <div v-if="currentStep === 1">
        <ImageUploader :disabled="isUploading" @upload="handleUpload" />
      </div>

      <!-- Step 2: Detection Results -->
      <div v-else-if="currentStep === 2 && currentResult">
        <div v-if="uploadedImageUrl" class="mb-6 flex justify-center">
          <DetectionImage :image-url="uploadedImageUrl" :detections="currentResult.detections" />
        </div>
        <DetectionList :detections="currentResult.detections" />

        <!-- Model Selection for LLM Judge -->
        <div class="mt-10 rounded-lg border p-4">
          <h3 class="mb-4 text-lg font-semibold">LLM 违规判定</h3>
          <NSpace vertical>
            <div class="flex items-center gap-4">
              <label class="w-20 shrink-0 text-sm text-gray-600">模型提供商</label>
              <NSelect
                v-model:value="selectedProviderId"
                :options="providers.map((p) => ({ label: p.name, value: p.id }))"
                placeholder="选择提供商"
                class="flex-1"
              />
            </div>
            <div class="flex items-center gap-4">
              <label class="w-20 shrink-0 text-sm text-gray-600">模型</label>
              <NSelect
                v-model:value="selectedModel"
                :options="availableModels.map((m) => ({ label: m, value: m }))"
                :disabled="!selectedProviderId"
                placeholder="选择已激活的模型"
                class="flex-1"
              />
            </div>
            <NButton
              type="primary"
              size="large"
              :disabled="!selectedProviderId || !selectedModel"
              :loading="isJudging"
              @click="handleJudge"
              block
            >
              开始判定
            </NButton>
          </NSpace>
        </div>
      </div>

      <!-- Step 3: Judge Result -->
      <div v-else-if="currentStep === 3 && judgeResult">
        <NCard
          :title="judgeResult.violated ? '违规判定' : '判定结果'"
          :class="judgeResult.violated ? 'border-red-300' : 'border-green-300'"
        >
          <div class="space-y-4">
            <div
              :class="[
                'rounded-lg p-6 text-center text-2xl font-bold',
                judgeResult.violated ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600',
              ]"
            >
              {{ judgeResult.violated ? '⚠️ 检测到违规行为' : '✅ 未检测到违规' }}
            </div>
            <div v-if="judgeResult.reason" class="rounded bg-gray-50 p-4 dark:bg-gray-800">
              <div class="mb-1 text-sm text-gray-500">判定理由</div>
              <div class="text-gray-800 dark:text-gray-200">{{ judgeResult.reason }}</div>
            </div>
          </div>
        </NCard>
      </div>

      <!-- Actions -->
      <div v-if="currentStep > 1" class="mt-6 flex gap-3">
        <NButton @click="handleReset">重新检测</NButton>
      </div>
    </NCard>
  </div>
</template>
