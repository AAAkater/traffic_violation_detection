<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
import { useThemeStore } from '@/stores/theme'
import { NConfigProvider, NMessageProvider, NDialogProvider, darkTheme, lightTheme } from 'naive-ui'
import { watchEffect, onMounted, onUnmounted } from 'vue'

const themeStore = useThemeStore()

// ---- 同步 <html class="dark"> ----
function syncHtmlClass() {
  document.documentElement.classList.toggle('dark', themeStore.isDark)
}

watchEffect(syncHtmlClass)

onMounted(() => {
  themeStore.initSystemListener()
  syncHtmlClass()
})

onUnmounted(() => {
  themeStore.teardownSystemListener()
})
</script>

<template>
  <NConfigProvider :theme="themeStore.isDark ? darkTheme : lightTheme" preflight-style-disabled>
    <NMessageProvider>
      <NDialogProvider>
        <AppLayout />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
