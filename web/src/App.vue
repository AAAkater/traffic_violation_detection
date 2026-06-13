<script setup lang="ts">
import { CameraOutline, TimeOutline, SettingsOutline, HomeOutline } from '@vicons/ionicons5'
import {
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NMenu,
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  type MenuOption,
} from 'naive-ui'
import { shallowRef, h, watch } from 'vue'
import { RouterView, useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const collapsed = shallowRef(false)

const menuOptions: MenuOption[] = [
  {
    label: '首页',
    key: 'home',
    icon: () => h(HomeOutline),
  },
  {
    label: '交通检测',
    key: 'detect',
    icon: () => h(CameraOutline),
  },
  {
    label: '历史记录',
    key: 'history',
    icon: () => h(TimeOutline),
  },
  {
    label: '系统设置',
    key: 'settings',
    icon: () => h(SettingsOutline),
  },
]

const activeKey = shallowRef(String(route.name ?? 'home'))

watch(
  () => route.name,
  (name) => {
    const key = String(name ?? 'home')
    activeKey.value = key.startsWith('history') ? 'history' : key
  },
)

function handleMenuUpdate(key: string) {
  router.push({ name: key })
}
</script>

<template>
  <NConfigProvider :theme="null">
    <NMessageProvider>
      <NDialogProvider>
        <NLayout has-sider position="absolute">
          <NLayoutSider
            bordered
            collapse-mode="width"
            :collapsed="collapsed"
            :collapsed-width="64"
            :width="220"
            show-trigger="arrow-circle"
            @collapse="collapsed = true"
            @expand="collapsed = false"
          >
            <div
              class="flex h-16 items-center justify-center border-b border-gray-100 dark:border-gray-800"
            >
              <span v-if="!collapsed" class="text-lg font-bold text-gray-800 dark:text-white">
                🚦 交通检测
              </span>
              <span v-else class="text-2xl">🚦</span>
            </div>
            <NMenu
              v-model:value="activeKey"
              :collapsed="collapsed"
              :collapsed-width="64"
              :options="menuOptions"
              @update:value="handleMenuUpdate"
            />
          </NLayoutSider>
          <NLayoutContent class="bg-gray-50 dark:bg-gray-900">
            <div class="h-full overflow-auto p-6">
              <RouterView />
            </div>
          </NLayoutContent>
        </NLayout>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
.n-layout {
  height: 100vh;
}
</style>
