<script setup lang="ts">
import PromptList from '@/components/settings/PromptList.vue'
import ProviderList from '@/components/settings/ProviderList.vue'
import { NTabs, NTabPane } from 'naive-ui'
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-3xl font-bold text-gray-800 dark:text-white">系统设置</h1>

    <NTabs type="line" animated>
      <NTabPane name="provider" tab="模型提供商">
        <div class="mt-4">
          <ProviderList />
        </div>
      </NTabPane>
      <NTabPane name="prompt" tab="提示词管理">
        <div class="mt-4">
          <PromptList />
        </div>
      </NTabPane>
    </NTabs>
  </div>
</template>
