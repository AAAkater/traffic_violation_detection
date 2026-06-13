<script setup lang="ts">
import { useHistoryStore } from '@/stores/history'
import { CameraOutline } from '@vicons/ionicons5'
import { NButton, NCard, NGrid, NGi, NStatistic, NTag } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const historyStore = useHistoryStore()
const { items, total, isLoading } = storeToRefs(historyStore)

onMounted(() => {
  historyStore.fetchHistory({ page: 1, page_size: 5 })
})

function goDetect() {
  router.push({ name: 'detect' })
}

function goHistory() {
  router.push({ name: 'history' })
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-3xl font-bold text-gray-800 dark:text-white">交通违规检测系统</h1>

    <NGrid :cols="3" :x-gap="16" responsive="screen">
      <NGi>
        <NCard>
          <NStatistic label="历史总记录" :value="total" />
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic
            label="违规记录"
            :value="(items ?? []).filter((i) => i.judge?.violated).length"
          />
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NStatistic label="未判定" :value="(items ?? []).filter((i) => !i.judge).length" />
        </NCard>
      </NGi>
    </NGrid>

    <div class="flex gap-4">
      <NButton type="primary" size="large" @click="goDetect">
        <template #icon>
          <CameraOutline />
        </template>
        开始检测
      </NButton>
    </div>

    <NCard title="最近记录">
      <template v-if="isLoading">
        <div class="py-8 text-center text-gray-400">加载中...</div>
      </template>
      <template v-else-if="items.length === 0">
        <div class="py-8 text-center text-gray-400">暂无记录，请先上传图片进行检测</div>
      </template>
      <template v-else>
        <div class="space-y-3">
          <div
            v-for="item in items"
            :key="item.image_id"
            class="flex cursor-pointer items-center justify-between rounded-lg border p-3 transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
            @click="router.push({ name: 'history-detail', params: { imageId: item.image_id } })"
          >
            <div class="flex items-center gap-3">
              <img
                v-if="item.image_url"
                :src="item.image_url"
                :alt="item.filename"
                class="h-12 w-12 rounded object-cover"
              />
              <div v-else class="h-12 w-12 rounded bg-gray-200 dark:bg-gray-700" />
              <div>
                <div class="font-medium">{{ item.filename }}</div>
                <div class="text-sm text-gray-500">{{ item.created_at }}</div>
              </div>
            </div>
            <NTag v-if="item.judge" :type="item.judge.violated ? 'error' : 'success'">
              {{ item.judge.violated ? '违规' : '正常' }}
            </NTag>
            <NTag v-else type="default">未判定</NTag>
          </div>
        </div>
        <div class="mt-4 text-center">
          <NButton text type="primary" @click="goHistory">查看全部</NButton>
        </div>
      </template>
    </NCard>
  </div>
</template>
