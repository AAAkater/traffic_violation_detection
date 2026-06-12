<script setup lang="ts">
import ProviderForm from './ProviderForm.vue'
import ProviderModelManager from './ProviderModelManager.vue'
import { useMessage } from '@/composables/useMessage'
import { useProviderStore } from '@/stores/provider'
import type { ProviderData, ProviderUpdate } from '@/types/api'
import { NButton, NDataTable, NModal, NSpace, NTag, NPopconfirm, NText } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { shallowRef, onMounted, h } from 'vue'

const providerStore = useProviderStore()
const { showSuccess, showError } = useMessage()

const showCreateModal = shallowRef(false)
const showEditModal = shallowRef(false)
const showModelsModal = shallowRef(false)
const editingProvider = shallowRef<ProviderData | null>(null)
const modelsProviderId = shallowRef<number | null>(null)

const columns: DataTableColumns<ProviderData> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名称', key: 'name', width: 150 },
  { title: 'API 地址', key: 'base_url', ellipsis: { tooltip: true } },
  {
    title: '已激活模型',
    key: 'activated_models',
    render: (row) =>
      row.activated_models?.length
        ? row.activated_models.map((m) =>
            h(NTag, { size: 'small', style: { marginRight: '4px' } }, () => m),
          )
        : h(NText, { depth: 3 }, () => '无'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    render: (row) => {
      return h(NSpace, null, () => [
        h(NButton, { size: 'small', onClick: () => openModels(row) }, () => '模型管理'),
        h(NButton, { size: 'small', onClick: () => openEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          {
            default: () => '确定删除？',
            trigger: () => h(NButton, { size: 'small', type: 'error' }, () => '删除'),
          },
        ),
      ])
    },
  },
]

onMounted(() => {
  providerStore.fetchAll()
})

function openCreate() {
  editingProvider.value = null
  showCreateModal.value = true
}

function openEdit(provider: ProviderData) {
  editingProvider.value = provider
  showEditModal.value = true
}

function openModels(provider: ProviderData) {
  modelsProviderId.value = provider.id
  showModelsModal.value = true
}

async function handleCreate(data: ProviderUpdate) {
  try {
    // name and base_url are required for create; api_key is also required
    if (!data.name || !data.base_url || !data.api_key) {
      showError('名称、API 地址和 API Key 为必填项')
      return
    }
    await providerStore.create({
      name: data.name,
      base_url: data.base_url,
      api_key: data.api_key,
    })
    showSuccess('创建成功')
    showCreateModal.value = false
  } catch (e) {
    showError(e instanceof Error ? e.message : '创建失败')
  }
}

async function handleUpdate(data: ProviderUpdate) {
  if (!editingProvider.value) return
  try {
    await providerStore.update(editingProvider.value.id, data)
    showSuccess('更新成功')
    showEditModal.value = false
  } catch (e) {
    showError(e instanceof Error ? e.message : '更新失败')
  }
}

async function handleDelete(id: number) {
  try {
    await providerStore.remove(id)
    showSuccess('删除成功')
  } catch (e) {
    showError(e instanceof Error ? e.message : '删除失败')
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-end">
      <NButton type="primary" @click="openCreate">添加提供商</NButton>
    </div>

    <NDataTable :columns="columns" :data="providerStore.providers" :bordered="false" />

    <!-- Create Modal -->
    <NModal v-model:show="showCreateModal" title="添加模型提供商">
      <ProviderForm @submit="handleCreate" @cancel="showCreateModal = false" />
    </NModal>

    <!-- Edit Modal -->
    <NModal v-model:show="showEditModal" title="编辑模型提供商">
      <ProviderForm
        :initial-data="editingProvider ?? undefined"
        @submit="handleUpdate"
        @cancel="showEditModal = false"
      />
    </NModal>

    <!-- Models Modal -->
    <NModal v-model:show="showModelsModal" title="模型管理">
      <ProviderModelManager v-if="modelsProviderId !== null" :provider-id="modelsProviderId" />
    </NModal>
  </div>
</template>
