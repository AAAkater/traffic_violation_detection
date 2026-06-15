import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type ThemeMode = 'system' | 'light' | 'dark'

export const useThemeStore = defineStore(
  'theme',
  () => {
    const mode = ref<ThemeMode>('system')
    const systemDark = ref(false)

    // ---- getters ----
    const isDark = computed(() =>
      mode.value === 'system' ? systemDark.value : mode.value === 'dark',
    )

    // ---- media query listener ----
    let mediaQuery: MediaQueryList | null = null

    function initSystemListener() {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      systemDark.value = mediaQuery.matches
      mediaQuery.addEventListener('change', (e) => {
        systemDark.value = e.matches
      })
    }

    function teardownSystemListener() {
      if (mediaQuery) {
        mediaQuery.removeEventListener('change', () => {})
        mediaQuery = null
      }
    }

    // ---- actions ----
    const modeCycle: ThemeMode[] = ['system', 'light', 'dark']

    function toggleMode() {
      const idx = modeCycle.indexOf(mode.value)
      mode.value = modeCycle[(idx + 1) % modeCycle.length]!
    }

    function setMode(newMode: ThemeMode) {
      mode.value = newMode
    }

    return {
      mode,
      systemDark,
      isDark,
      initSystemListener,
      teardownSystemListener,
      toggleMode,
      setMode,
    }
  },
  {
    persist: {
      pick: ['mode'],
    },
  },
)
