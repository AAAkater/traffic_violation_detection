<script setup lang="ts">
import { useMessage } from '@/composables/useMessage'
import { usePromptStore } from '@/stores/prompt'
import { NButton, NList, NListItem, NTag, NModal, NInput, NForm, NFormItem, NSpace } from 'naive-ui'
import { shallowRef, onMounted } from 'vue'

const promptStore = usePromptStore()
const { showSuccess, showError } = useMessage()

const showCreateModal = shallowRef(false)
const newName = shallowRef('')
const newContent = shallowRef('')

onMounted(() => {
  promptStore.fetchList()
  promptStore.fetchActive()
})

async function handleCreate() {
  if (!newName.value || !newContent.value) return
  try {
    await promptStore.set(newName.value, newContent.value)
    showSuccess('设置成功')
    showCreateModal.value = false
    newName.value = ''
    newContent.value = ''
    promptStore.fetchList()
  } catch (e) {
    showError(e instanceof Error ? e.message : '设置失败')
  }
}

async function handleSetActive(name: string, content: string) {
  try {
    await promptStore.set(name, content)
    showSuccess(`已激活 "${name}"`)
    promptStore.fetchList()
  } catch (e) {
    showError(e instanceof Error ? e.message : '激活失败')
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-end">
      <NButton type="primary" @click="showCreateModal = true">新建提示词</NButton>
    </div>

    <NList>
      <NListItem v-for="prompt in promptStore.promptList" :key="prompt.name">
        <div class="flex w-full items-center justify-between gap-4">
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ prompt.name }}</span>
              <NTag v-if="prompt.is_active" type="success" size="small">激活</NTag>
            </div>
            <div class="mt-1 text-sm text-gray-500 line-clamp-2">
              {{ prompt.content }}
            </div>
            <div class="mt-1 text-xs text-gray-400">{{ prompt.updated_at }}</div>
          </div>
          <NButton
            v-if="!prompt.is_active"
            size="small"
            @click="handleSetActive(prompt.name, prompt.content)"
          >
            设为激活
          </NButton>
        </div>
      </NListItem>
    </NList>

    <!-- Create Modal -->
    <NModal v-model:show="showCreateModal" title="新建提示词">
      <NForm class="w-[480px] max-w-full" @submit.prevent="handleCreate">
        <NFormItem label="名称" required>
          <NInput v-model:value="newName" placeholder="例如: red-light-judge" />
        </NFormItem>
        <NFormItem label="内容" required>
          <NInput
            v-model:value="newContent"
            type="textarea"
            :rows="8"
            placeholder="输入系统提示词..."
          />
        </NFormItem>
        <NSpace justify="end">
          <NButton @click="showCreateModal = false">取消</NButton>
          <NButton type="primary" attr-type="submit">创建</NButton>
        </NSpace>
      </NForm>
    </NModal>
  </div>
</template>
