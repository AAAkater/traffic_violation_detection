<script setup lang="ts">
import type { ProviderData, ProviderCreate, ProviderUpdate } from '@/types/api'
import { NForm, NFormItem, NInput, NButton, NSpace, NText } from 'naive-ui'
import { shallowRef } from 'vue'

const props = defineProps<{
  initialData?: ProviderData
}>()

const emit = defineEmits<{
  submit: [data: ProviderCreate | ProviderUpdate]
  cancel: []
}>()

const name = shallowRef(props.initialData?.name ?? '')
const baseUrl = shallowRef(props.initialData?.base_url ?? '')
const apiKey = shallowRef('')

const isEdit = !!props.initialData

function handleSubmit() {
  emit('submit', {
    name: name.value || undefined,
    base_url: baseUrl.value || undefined,
    api_key: apiKey.value || undefined,
  })
}
</script>

<template>
  <NForm class="w-96 max-w-full" @submit.prevent="handleSubmit">
    <NFormItem label="名称" required>
      <NInput v-model:value="name" placeholder="例如: OpenAI" />
    </NFormItem>
    <NFormItem label="API 地址" required>
      <NInput v-model:value="baseUrl" placeholder="https://api.openai.com/v1" />
    </NFormItem>
    <NFormItem label="API Key" :required="!isEdit">
      <NInput
        v-model:value="apiKey"
        type="password"
        show-password-on="click"
        :placeholder="isEdit ? '留空则不修改' : 'sk-...'"
      />
    </NFormItem>
    <NSpace justify="end">
      <NButton @click="emit('cancel')">取消</NButton>
      <NButton type="primary" attr-type="submit">确定</NButton>
    </NSpace>
  </NForm>
</template>
