<script setup lang="ts">
import type { DetectionItem } from '@/types/api'
import { splitAndCompressQuadrants, type DetectionBox } from '@/utils/image'
import { NImage, NImageGroup, useThemeVars } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { shallowRef, computed, watch } from 'vue'

const { imageUrl, detections } = defineProps<{
  imageUrl: string
  detections: DetectionItem[]
}>()

const quadrantUrls = shallowRef<Record<string, string>>({})
const quadrantAspect = shallowRef(1)

// ---- NImageGroup 暗色工具栏适配 ----
const imageGroupThemeOverrides = computed<NonNullable<GlobalThemeOverrides['Image']>>(() => {
  const { popoverColor, boxShadow2, textColor2, borderRadius } = useThemeVars().value
  return {
    toolbarColor: popoverColor,
    toolbarBoxShadow: boxShadow2,
    toolbarIconColor: textColor2,
    toolbarBorderRadius: borderRadius,
  }
})

function groupBoxes(list: DetectionItem[]): Record<string, DetectionBox[]> {
  const map: Record<string, DetectionBox[]> = {
    top_left: [],
    top_right: [],
    bottom_left: [],
    bottom_right: [],
  }
  for (const d of list) {
    const boxes = map[d.quadrant]
    if (boxes) {
      boxes.push({ bbox: d.bbox, class_name: d.class_name, confidence: d.confidence })
    }
  }
  return map
}

/**
 * 用 fetch 下载图片转 blob URL（绕过 Canvas CORS 污染）。
 * 对齐后端：先拿原始分辨率图，Canvas 裁剪 + 压缩 + 画框。
 */
async function processImage(url: string) {
  if (!url) return
  const boxesByQuadrant = groupBoxes(detections)

  const resp = await fetch(url)
  const blob = await resp.blob()
  const blobUrl = URL.createObjectURL(blob)

  const img = new Image()
  img.onload = () => {
    const hw = Math.floor(img.naturalWidth / 2)
    const hh = Math.floor(img.naturalHeight / 2)
    quadrantAspect.value = hw / hh
    quadrantUrls.value = splitAndCompressQuadrants(img, boxesByQuadrant)
    // 释放临时 blob
    URL.revokeObjectURL(blobUrl)
  }
  img.onerror = () => {
    URL.revokeObjectURL(blobUrl)
  }
  img.src = blobUrl
}

// 首次加载
processImage(imageUrl)

// imageUrl 变化时重新处理
watch(() => imageUrl, processImage)

const quadrantOrder = ['top_left', 'top_right', 'bottom_left', 'bottom_right'] as const

const quadrantLabel: Record<string, string> = {
  top_left: '↖ 左上象限',
  top_right: '↗ 右上象限',
  bottom_left: '↙ 左下象限',
  bottom_right: '↘ 右下象限',
}
</script>

<template>
  <div class="w-full">
    <div v-if="Object.keys(quadrantUrls).length > 0" class="grid grid-cols-2 gap-3">
      <NImageGroup :theme-overrides="imageGroupThemeOverrides">
        <div
          v-for="q in quadrantOrder"
          :key="q"
          class="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-gray-800"
        >
          <div class="px-3 py-2 text-sm font-semibold text-gray-600 dark:text-gray-300">
            {{ quadrantLabel[q] }}
          </div>
          <div :style="{ aspectRatio: `${quadrantAspect}` }">
            <NImage :src="quadrantUrls[q]" />
          </div>
        </div>
      </NImageGroup>
    </div>

    <div
      v-else
      class="flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-700 py-12"
    >
      <span class="text-gray-400 dark:text-gray-500">图片加载中…</span>
    </div>
  </div>
</template>
