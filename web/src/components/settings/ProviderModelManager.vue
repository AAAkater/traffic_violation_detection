<script setup lang="ts">
import { useMessage } from '@/composables/useMessage'
import { useProviderStore } from '@/stores/provider'
import { NButton, NList, NListItem, NTag, NSpin, NSpace, NPopconfirm } from 'naive-ui'
import { shallowRef, onMounted, h } from 'vue'

const props = defineProps<{
  providerId: number
}>()

const providerStore = useProviderStore()
const { showSuccess, showError } = useMessage()
const isLoading = shallowRef(false)
const allModels = shallowRef<{ id: string }[]>([])
const activatedModelSet = shallowRef<Set<string>>(new Set())

onMounted(async () => {
  await loadData()
})

async function loadData() {
  isLoading.value = true
  try {
    const modelsData = await providerStore.fetchModels(props.providerId)
    allModels.value = modelsData.models
    const activated = await providerStore.fetchActivatedModels(props.providerId)
    activatedModelSet.value = new Set(activated)
  } catch {
    showError('加载模型列表失败')
  } finally {
    isLoading.value = false
  }
}

async function handleActivate(model: string) {
  try {
    await providerStore.activateModel(props.providerId, model)
    activatedModelSet.value = new Set([...activatedModelSet.value, model])
    showSuccess(`已激活 ${model}`)
  } catch (e) {
    showError(e instanceof Error ? e.message : '激活失败')
  }
}

async function handleDeactivate(model: string) {
  try {
    await providerStore.deactivateModel(props.providerId, model)
    const set = new Set(activatedModelSet.value)
    set.delete(model)
    activatedModelSet.value = set
    showSuccess(`已停用 ${model}`)
  } catch (e) {
    showError(e instanceof Error ? e.message : '停用失败')
  }
}
</script>

<template>
  <NSpin :show="isLoading">
    <NList class="w-96 max-w-full">
      <NListItem v-for="model in allModels" :key="model.id">
        <div class="flex w-full items-center justify-between">
          <span>{{ model.id }}</span>
          <NButton
            v-if="activatedModelSet.has(model.id)"
            size="small"
            type="warning"
            @click="handleDeactivate(model.id)"
          >
            停用
          </NButton>
          <NButton v-else size="small" type="primary" @click="handleActivate(model.id)">
            激活
          </NButton>
        </div>
      </NListItem>
      <NListItem v-if="allModels.length === 0">
        <div class="py-8 w-full text-center text-gray-400">暂无可用的模型</div>
      </NListItem>
    </NList>
  </NSpin>
</template>
