<script setup lang="ts">
import { useMessage } from '@/composables/useMessage'
import { useProviderStore } from '@/stores/provider'
import { NButton, NSpin, NDataTable, NPagination, NInput } from 'naive-ui'
import { shallowRef, computed, onMounted, h, watch } from 'vue'

const props = defineProps<{
  providerId: number
}>()

const providerStore = useProviderStore()
const { showSuccess, showError } = useMessage()
const isLoading = shallowRef(false)
const allModels = shallowRef<{ id: string }[]>([])
const activatedModelSet = shallowRef<Set<string>>(new Set())
const searchQuery = shallowRef('')
const currentPage = shallowRef(1)
const pageSize = shallowRef(10)

const filteredModels = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return allModels.value
  return allModels.value.filter((m) => m.id.toLowerCase().includes(q))
})

const paginatedModels = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredModels.value.slice(start, start + pageSize.value)
})

watch(searchQuery, () => {
  currentPage.value = 1
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

const columns = computed(() => [
  { title: '模型名称', key: 'id', ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row: { id: string }) => {
      if (activatedModelSet.value.has(row.id)) {
        return h(
          NButton,
          { size: 'tiny', type: 'warning', onClick: () => handleDeactivate(row.id) },
          () => '停用',
        )
      }
      return h(
        NButton,
        { size: 'tiny', type: 'primary', onClick: () => handleActivate(row.id) },
        () => '激活',
      )
    },
  },
])

onMounted(() => {
  loadData()
})
</script>

<template>
  <div style="width: 560px" class="bg-white dark:bg-gray-800 rounded-lg p-3">
    <div class="mb-3">
      <NInput v-model:value="searchQuery" placeholder="搜索模型名称..." clearable />
    </div>
    <NSpin :show="isLoading">
      <NDataTable
        :columns="columns"
        :data="paginatedModels"
        :bordered="false"
        :single-line="false"
        max-height="400"
      />
      <div v-if="filteredModels.length > pageSize" class="flex justify-center pt-3">
        <NPagination
          v-model:page="currentPage"
          v-model:page-size="pageSize"
          :item-count="filteredModels.length"
          :page-sizes="[10, 20, 50, 100]"
          show-size-picker
          :page-slot="7"
        />
      </div>
    </NSpin>
  </div>
</template>
