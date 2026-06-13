<script setup lang="ts">
import { CloudUploadOutline } from '@vicons/ionicons5'
import { NUpload, NUploadDragger, NButton, NIcon, NP, NSpin } from 'naive-ui'
import type { UploadFileInfo } from 'naive-ui'

defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  upload: [file: File]
}>()

function handleChange(options: { file: UploadFileInfo; fileList: UploadFileInfo[] }) {
  if (options.file?.file) {
    emit('upload', options.file.file)
  }
}
</script>

<template>
  <NUpload :disabled="disabled" accept="image/*" :max="1" directory-dnd @change="handleChange">
    <NUploadDragger>
      <div class="flex flex-col items-center gap-3 py-6">
        <NSpin v-if="disabled" size="medium" />
        <NIcon v-else size="36" color="#9ca3af">
          <CloudUploadOutline />
        </NIcon>
        <NButton type="primary" size="large" :disabled="disabled" tag="div">
          {{ disabled ? '检测中...' : '选择图片上传' }}
        </NButton>
        <NP v-if="!disabled" class="text-sm text-gray-400">或拖拽图片到此区域</NP>
      </div>
    </NUploadDragger>
  </NUpload>
</template>
