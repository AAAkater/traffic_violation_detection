<script setup lang="ts">
import { useHistoryStore } from '@/stores/history'
import { NCard, NTag, NSpin, NDescriptions, NDescriptionsItem } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const historyStore = useHistoryStore()
const { items, isLoading } = storeToRefs(historyStore)

const imageId = computed(() => String(route.params.imageId))

const item = computed(() => items.value.find((i) => i.image_id === imageId.value))

onMounted(() => {
  if (!item.value) {
    historyStore.fetchHistory({ page: 1, page_size: 100 })
  }
})
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <NSpin :show="isLoading">
      <template v-if="item">
        <h1 class="text-2xl font-bold text-gray-800 dark:text-white">
          检测详情 - {{ item.filename }}
        </h1>

        <!-- Image -->
        <NCard v-if="item.image_url">
          <img
            :src="item.image_url"
            :alt="item.filename"
            class="max-h-96 w-full rounded object-contain"
          />
        </NCard>

        <!-- Detections Table -->
        <NCard title="检测结果">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead>
                <tr class="border-b dark:border-gray-700">
                  <th class="py-2 pr-4">类别</th>
                  <th class="py-2 pr-4">置信度</th>
                  <th class="py-2 pr-4">象限</th>
                  <th class="py-2">坐标</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(det, i) in item.detections ?? []"
                  :key="i"
                  class="border-b dark:border-gray-700"
                >
                  <td class="py-2 pr-4">
                    <NTag size="small">{{ det.class_name }}</NTag>
                  </td>
                  <td class="py-2 pr-4">{{ (det.confidence * 100).toFixed(1) }}%</td>
                  <td class="py-2 pr-4">{{ det.quadrant }}</td>
                  <td class="py-2 text-xs text-gray-500">[{{ det.bbox.join(', ') }}]</td>
                </tr>
              </tbody>
            </table>
          </div>
        </NCard>

        <!-- Judge Result -->
        <NCard v-if="item.judge" title="判定结果">
          <NDescriptions bordered>
            <NDescriptionsItem label="判定结果">
              <NTag :type="item.judge.violated ? 'error' : 'success'">
                {{ item.judge.violated ? '违规' : '正常' }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem v-if="item.judge.reason" label="判定理由">
              {{ item.judge.reason }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="item.judge.prompt_name" label="提示词">
              {{ item.judge.prompt_name }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="item.judge.provider_id" label="提供商 ID">
              {{ item.judge.provider_id }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="item.judge.model" label="模型">
              {{ item.judge.model }}
            </NDescriptionsItem>
          </NDescriptions>
        </NCard>

        <NCard v-else title="判定状态">
          <div class="py-8 text-center text-gray-400">尚未进行 AI 判定</div>
        </NCard>
      </template>
      <div v-else class="py-12 text-center text-gray-400">未找到该记录</div>
    </NSpin>
  </div>
</template>
