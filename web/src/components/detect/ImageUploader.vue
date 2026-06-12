<script setup lang="ts">
import { ImageOutline } from '@vicons/ionicons5'
import { NUpload, NUploadDragger, NText, NP } from 'naive-ui'
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
      <div class="flex flex-col items-center py-12">
        <ImageOutline class="text-5xl text-gray-400" />
        <NText class="mt-4 text-lg">点击或拖拽上传交通图片</NText>
        <NP class="mt-1 text-gray-400">支持 JPG、PNG、WebP 格式</NP>
      </div>
    </NUploadDragger>
  </NUpload>
</template>
