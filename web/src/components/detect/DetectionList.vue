<script setup lang="ts">
import type { DetectionItem } from '@/types/api'
import { NTable, NTag } from 'naive-ui'
import { computed } from 'vue'

const props = defineProps<{
  detections: DetectionItem[]
}>()

const columns = [
  { title: '类别', key: 'class_name', width: 120 },
  { title: '置信度', key: 'confidence', width: 100 },
  { title: '象限', key: 'quadrant', width: 160 },
  { title: '坐标', key: 'bbox' },
]

const data = computed(() =>
  props.detections.map((d, i) => ({
    ...d,
    key: i,
  })),
)

function getTagType(className: string) {
  switch (className) {
    case 'red':
      return 'error'
    case 'green':
      return 'success'
    case 'yellow':
      return 'warning'
    default:
      return 'default'
  }
}
</script>

<template>
  <NTable :columns="columns" :data="data" :bordered="false" size="small">
    <template #class_name="{ row }">
      <NTag :type="getTagType(row.class_name)" size="small">
        {{ row.class_name }}
      </NTag>
    </template>
    <template #confidence="{ row }"> {{ (row.confidence * 100).toFixed(1) }}% </template>
    <template #bbox="{ row }">
      <span class="text-xs text-gray-500"> [{{ row.bbox.join(', ') }}] </span>
    </template>
  </NTable>
</template>
