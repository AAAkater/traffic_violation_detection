<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import {
  CameraOutline,
  TimeOutline,
  SettingsOutline,
  HomeOutline,
  SunnyOutline,
  MoonOutline,
  LaptopOutline,
} from '@vicons/ionicons5'
import {
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NMenu,
  NButton,
  NIcon,
  NDropdown,
  type MenuOption,
  type DropdownOption,
} from 'naive-ui'
import { shallowRef, h, watch, type Component } from 'vue'
import { RouterView, useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const themeStore = useThemeStore()

const collapsed = shallowRef(false)

// ---- 图标渲染辅助 ----
function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// ---- 菜单 ----
const menuOptions: MenuOption[] = [
  {
    label: '首页',
    key: 'home',
    icon: renderIcon(HomeOutline),
  },
  {
    label: '交通检测',
    key: 'detect',
    icon: renderIcon(CameraOutline),
  },
  {
    label: '历史记录',
    key: 'history',
    icon: renderIcon(TimeOutline),
  },
  {
    label: '系统设置',
    key: 'settings',
    icon: renderIcon(SettingsOutline),
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

// ---- 主题下拉 ----
const themeOptions: DropdownOption[] = [
  {
    label: '跟随系统',
    key: 'system',
    icon: renderIcon(LaptopOutline),
  },
  {
    label: '亮色模式',
    key: 'light',
    icon: renderIcon(SunnyOutline),
  },
  {
    label: '暗色模式',
    key: 'dark',
    icon: renderIcon(MoonOutline),
  },
]

const iconByMode: Record<string, typeof SunnyOutline> = {
  system: LaptopOutline,
  light: SunnyOutline,
  dark: MoonOutline,
}

const labelByMode: Record<string, string> = {
  system: '跟随系统',
  light: '亮色模式',
  dark: '暗色模式',
}

function handleThemeSelect(key: string) {
  themeStore.setMode(key as 'system' | 'light' | 'dark')
}
</script>

<template>
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

      <div
        class="absolute bottom-0 left-0 right-0 border-t border-gray-100 px-3 py-3 dark:border-gray-800"
      >
        <NDropdown
          placement="top"
          :options="themeOptions"
          :value="themeStore.mode"
          @select="handleThemeSelect"
        >
          <NButton
            quaternary
            :circle="collapsed"
            size="small"
            class="mx-auto flex items-center gap-1.5"
          >
            <template #icon>
              <NIcon>
                <component :is="iconByMode[themeStore.mode]" />
              </NIcon>
            </template>
            <span v-if="!collapsed" class="text-xs">{{ labelByMode[themeStore.mode] }}</span>
          </NButton>
        </NDropdown>
      </div>
    </NLayoutSider>

    <NLayoutContent class="bg-gray-50 dark:bg-gray-900">
      <div class="h-full overflow-auto p-6">
        <RouterView />
      </div>
    </NLayoutContent>
  </NLayout>
</template>

<style scoped>
.n-layout {
  height: 100vh;
}
</style>
