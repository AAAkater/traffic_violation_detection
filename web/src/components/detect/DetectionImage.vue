<script setup lang="ts">
import type { DetectionItem } from '@/types/api'
import { NImage, NCard, NTag } from 'naive-ui'
import type { CSSProperties } from 'vue'
import { shallowRef, computed } from 'vue'

const { imageUrl, detections } = defineProps<{
  imageUrl: string
  detections: DetectionItem[]
}>()

const naturalWidth = shallowRef(0)
const naturalHeight = shallowRef(0)

const halfW = computed(() => naturalWidth.value / 2)
const halfH = computed(() => naturalHeight.value / 2)

function onImageLoad(e: Event) {
  const img = e.target as HTMLImageElement
  naturalWidth.value = img.naturalWidth
  naturalHeight.value = img.naturalHeight
}

const quadrantOrder = ['top_left', 'top_right', 'bottom_left', 'bottom_right']

const quadrantLabel: Record<string, string> = {
  top_left: '↖ 左上象限',
  top_right: '↗ 右上象限',
  bottom_left: '↙ 左下象限',
  bottom_right: '↘ 右下象限',
}

function getDetections(quadrant: string): DetectionItem[] {
  return detections.filter((d) => d.quadrant === quadrant)
}

/** Position the full image (scaled 200%) so only the relevant quadrant fills the container */
function getImageOffset(quadrant: string): CSSProperties {
  const base: CSSProperties = {
    position: 'absolute',
    display: 'block',
    width: '200%',
    height: '200%',
    maxWidth: 'none',
    objectFit: 'fill',
  }
  switch (quadrant) {
    case 'top_left':
      return { ...base, left: '0', top: '0' }
    case 'top_right':
      return { ...base, left: '-100%', top: '0' }
    case 'bottom_left':
      return { ...base, left: '0', top: '-100%' }
    case 'bottom_right':
      return { ...base, left: '-100%', top: '-100%' }
    default:
      return base
  }
}

function getBoxStyle(bbox: [number, number, number, number]): CSSProperties {
  const [x1, y1, x2, y2] = bbox
  return {
    left: `${x1 * 100}%`,
    top: `${y1 * 100}%`,
    width: `${(x2 - x1) * 100}%`,
    height: `${(y2 - y1) * 100}%`,
  }
}

const boxColors: Record<string, string> = {
  red: 'border-red-500 bg-red-500/15',
  green: 'border-green-500 bg-green-500/15',
  yellow: 'border-yellow-500 bg-yellow-500/15',
}

function getBoxColor(className: string): string {
  return boxColors[className] ?? 'border-blue-500 bg-blue-500/15'
}
</script>

<template>
  <div class="w-full">
    <img :src="imageUrl" alt="" class="hidden" @load="onImageLoad" />

    <div v-if="naturalWidth > 0" class="grid grid-cols-2 gap-3">
      <NCard
        v-for="q in quadrantOrder"
        :key="q"
        size="small"
        :title="quadrantLabel[q]"
        header-class="text-sm! font-semibold! py-2! px-3!"
        content-class="p-0!"
      >
        <div class="relative overflow-hidden" :style="{ aspectRatio: `${halfW}/${halfH}` }">
          <NImage :src="imageUrl" :img-props="{ style: getImageOffset(q) }" />
          <div
            v-for="(det, i) in getDetections(q)"
            :key="i"
            :style="getBoxStyle(det.bbox)"
            :class="['absolute border-2 rounded', getBoxColor(det.class_name)]"
          >
            <NTag
              :type="
                det.class_name === 'red'
                  ? 'error'
                  : det.class_name === 'yellow'
                    ? 'warning'
                    : 'success'
              "
              size="small"
              class="absolute! -top-3! left-0!"
              round
            >
              {{ det.class_name }} {{ (det.confidence * 100).toFixed(0) }}%
            </NTag>
          </div>
        </div>
      </NCard>
    </div>

    <div
      v-else
      class="flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 py-12"
    >
      <span class="text-gray-400 dark:text-gray-500">图片加载中…</span>
    </div>
  </div>
</template>
