<script setup lang="ts">
import type { DetectionItem } from '@/types/api'
import { NModal } from 'naive-ui'
import type { CSSProperties } from 'vue'
import { shallowRef, computed } from 'vue'

const { imageUrl, detections } = defineProps<{
  imageUrl: string
  detections: DetectionItem[]
}>()

const naturalWidth = shallowRef(0)
const naturalHeight = shallowRef(0)
const previewQuadrant = shallowRef<string | null>(null)

const showPreview = computed({
  get: () => previewQuadrant.value !== null,
  set: (v: boolean) => {
    if (!v) previewQuadrant.value = null
  },
})

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

const labelColors: Record<string, string> = {
  red: 'bg-red-500 text-white',
  green: 'bg-green-500 text-white',
  yellow: 'bg-yellow-500 text-black',
}

function getBoxColor(className: string): string {
  return boxColors[className] ?? 'border-blue-500 bg-blue-500/15'
}

function getLabelColor(className: string): string {
  return labelColors[className] ?? 'bg-blue-500 text-white'
}
</script>

<template>
  <div class="w-full">
    <img :src="imageUrl" alt="" class="hidden" @load="onImageLoad" />

    <div v-if="naturalWidth > 0" class="grid grid-cols-2 gap-2">
      <div
        v-for="q in quadrantOrder"
        :key="q"
        class="cursor-pointer overflow-hidden rounded-lg border border-gray-200 hover:border-blue-400 hover:shadow-md transition-all"
        @click="previewQuadrant = q"
      >
        <div class="bg-gray-100 px-3 py-1.5 text-sm font-semibold text-gray-600">
          {{ quadrantLabel[q] ?? q }}
        </div>
        <div class="relative overflow-hidden" :style="{ aspectRatio: `${halfW}/${halfH}` }">
          <img :src="imageUrl" alt="" :style="getImageOffset(q)" />
          <div
            v-for="(det, i) in getDetections(q)"
            :key="i"
            :style="getBoxStyle(det.bbox)"
            :class="['absolute border-2 rounded', getBoxColor(det.class_name)]"
          >
            <span
              :class="[
                'absolute -top-5.5 left-0 text-xs font-semibold px-1.5 py-0.5 rounded whitespace-nowrap',
                getLabelColor(det.class_name),
              ]"
            >
              {{ det.class_name }} {{ (det.confidence * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex items-center justify-center rounded-lg border border-gray-200 py-12">
      <span class="text-gray-400">图片加载中…</span>
    </div>

    <!-- Preview Modal -->
    <NModal v-model:show="showPreview" title="象限预览" style="width: 90vw; max-width: 1200px">
      <div v-if="previewQuadrant" class="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div class="text-center text-lg font-semibold mb-4">
          {{ quadrantLabel[previewQuadrant] ?? previewQuadrant }}
        </div>
        <div
          class="relative overflow-hidden rounded-lg border border-gray-200"
          :style="{ width: '100%', aspectRatio: `${naturalWidth / 2}/${naturalHeight / 2}` }"
        >
          <img :src="imageUrl" alt="" :style="getImageOffset(previewQuadrant)" />
          <div
            v-for="(det, i) in getDetections(previewQuadrant!)"
            :key="i"
            :style="getBoxStyle(det.bbox)"
            :class="['absolute border-2 rounded', getBoxColor(det.class_name)]"
          >
            <span
              :class="[
                'absolute -top-5.5 left-0 text-xs font-semibold px-1.5 py-0.5 rounded whitespace-nowrap',
                getLabelColor(det.class_name),
              ]"
            >
              {{ det.class_name }} {{ (det.confidence * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
      </div>
    </NModal>
  </div>
</template>
