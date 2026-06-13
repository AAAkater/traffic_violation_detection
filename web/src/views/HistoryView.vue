<script setup lang="ts">
import { useHistoryStore } from '@/stores/history'
import { NPagination, NSpin, NCard, NTag } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const historyStore = useHistoryStore()
const { items, total, pageSize, isLoading } = storeToRefs(historyStore)

const currentPage = computed({
  get: () => Number(route.query.page) || 1,
  set: (value) => {
    router.push({ query: { ...route.query, page: value === 1 ? undefined : value } })
  },
})

onMounted(() => {
  historyStore.fetchHistory({
    page: currentPage.value,
    page_size: pageSize.value,
  })
})

watch(currentPage, (newPage) => {
  historyStore.fetchHistory({ page: newPage, page_size: pageSize.value })
})

function goDetail(imageId: string) {
  router.push({ name: 'history-detail', params: { imageId } })
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-3xl font-bold text-gray-800 dark:text-white">历史记录</h1>

    <NSpin :show="isLoading">
      <NCard>
        <template v-if="items.length === 0">
          <div class="py-12 text-center text-gray-400">暂无历史记录</div>
        </template>
        <template v-else>
          <div class="space-y-3">
            <div
              v-for="item in items"
              :key="item.image_id"
              class="flex cursor-pointer items-center gap-4 rounded-lg border p-4 transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
              @click="goDetail(item.image_id)"
            >
              <img
                v-if="item.image_url"
                :src="item.image_url"
                :alt="item.filename"
                class="h-16 w-16 rounded object-cover"
              />
              <div v-else class="h-16 w-16 rounded bg-gray-200 dark:bg-gray-700" />
              <div class="flex-1">
                <div class="font-medium">{{ item.filename }}</div>
                <div class="text-sm text-gray-500">{{ item.created_at }}</div>
                <div class="mt-1 text-xs text-gray-400">
                  {{ item.detections?.length ?? 0 }} 个检测框
                </div>
              </div>
              <NTag v-if="item.judge" :type="item.judge.violated ? 'error' : 'success'" round>
                {{ item.judge.violated ? '违规' : '正常' }}
              </NTag>
              <NTag v-else type="default" round>未判定</NTag>
            </div>
          </div>

          <div class="mt-6 flex justify-center">
            <NPagination v-model:page="currentPage" :page-size="pageSize" :item-count="total" />
          </div>
        </template>
      </NCard>
    </NSpin>
  </div>
</template>
