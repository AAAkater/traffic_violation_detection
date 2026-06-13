<script setup lang="ts">
import { judge } from '@/api/judge'
import { useMessage } from '@/composables/useMessage'
import { useProviderStore } from '@/stores/provider'
import type { ProviderData, JudgeData } from '@/types/api'
import { NSelect, NButton, NSpace, NSpin } from 'naive-ui'
import { shallowRef, ref, onMounted, watch } from 'vue'

const props = defineProps<{
  imageId: string
}>()

const emit = defineEmits<{
  judged: [result: JudgeData]
}>()

const providerStore = useProviderStore()
const { showError } = useMessage()

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
})

watch(selectedProviderId, async (id) => {
  if (id === null) return
  try {
    const models = await providerStore.fetchActivatedModels(id)
    availableModels.value = models
    selectedModel.value = null
  } catch {
    showError('获取模型列表失败')
  }
})

async function handleJudge() {
  if (!selectedProviderId.value || !selectedModel.value) return
  isJudging.value = true
  try {
    const result = await judge({
      image_id: props.imageId,
      provider_id: selectedProviderId.value,
      model: selectedModel.value,
    })
    emit('judged', result)
  } catch (e) {
    showError(e instanceof Error ? e.message : '判定失败')
  } finally {
    isJudging.value = false
  }
}
</script>

<template>
  <div class="rounded-lg border p-4">
    <h3 class="mb-4 text-lg font-semibold">LLM 违规判定</h3>

    <NSpace vertical>
      <div class="flex items-center gap-4">
        <label class="w-20 text-sm text-gray-600">模型提供商</label>
        <NSelect
          v-model:value="selectedProviderId"
          :options="providers.map((p) => ({ label: p.name, value: p.id }))"
          placeholder="选择提供商"
          class="flex-1"
        />
      </div>

      <div class="flex items-center gap-4">
        <label class="w-20 text-sm text-gray-600">模型</label>
        <NSelect
          v-model:value="selectedModel"
          :options="availableModels.map((m) => ({ label: m, value: m }))"
          :disabled="!selectedProviderId"
          placeholder="选择模型"
          class="flex-1"
        />
      </div>

      <NButton
        type="primary"
        :disabled="!selectedProviderId || !selectedModel"
        :loading="isJudging"
        @click="handleJudge"
        block
      >
        开始判定
      </NButton>
    </NSpace>
  </div>
</template>
