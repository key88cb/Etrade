<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import {
  BarChart3,
  Activity,
  Sun,
  Moon,
} from 'lucide-vue-next';

import DataManagement from '../components/dashboard/DataManagement.vue';
import { isDarkMode, setThemeMode, getThemeMode } from '../utils/theme';

type Theme = 'light' | 'dark';
const router = useRouter();

const currentTime = ref(new Date().toLocaleTimeString('en-US'));
let timer: ReturnType<typeof setInterval> | null = null;

// 使用全局主题系统
const darkModeState = ref(isDarkMode());
const isDark = computed(() => darkModeState.value);
const theme = computed<Theme>(() => isDark.value ? 'dark' : 'light');

const updateDarkModeState = () => {
  darkModeState.value = isDarkMode();
};

const toggleTheme = () => {
  const currentMode = getThemeMode();
  if (currentMode === 'auto') {
    // 如果当前是 auto，切换到与当前实际主题相反的模式
    setThemeMode(isDark.value ? 'light' : 'dark');
  } else {
    // 切换 light/dark
    setThemeMode(currentMode === 'dark' ? 'light' : 'dark');
  }
  // 更新状态
  updateDarkModeState();
};

onMounted(() => {
  timer = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('en-US');
  }, 1000);
  
  // 监听主题变化
  const observer = new MutationObserver(() => {
    updateDarkModeState();
  });
  
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  });
  
  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handleSystemThemeChange = () => {
    if (getThemeMode() === 'auto') {
      updateDarkModeState();
    }
  };
  
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handleSystemThemeChange);
  } else {
    mediaQuery.addListener(handleSystemThemeChange);
  }
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div :class="['min-h-screen transition-colors', isDark ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]']">
    <div class="relative">
      <header
        :class="[
          'border-b',
          isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]',
        ]"
      >
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 bg-[#238636] rounded flex items-center justify-center">
                <BarChart3 class="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 class="font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">概览</h1>
                <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">数据与任务</p>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <button
                type="button"
                @click="router.push('/app/comparison')"
                :class="[
                  'px-2.5 py-1.5 rounded-md transition-colors border text-xs',
                  isDark
                    ? 'bg-[#21262d] border-[#30363d] text-[#e6edf3] hover:border-[#58a6ff]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] hover:border-[#0969da]',
                ]"
                title="打开价格对比页面"
              >
                价格对比
              </button>


              <div
                class="flex items-center gap-2 px-2.5 py-1 rounded-md"
                :class="
                  isDark
                    ? 'bg-[#238636]/10 border border-[#238636]/30'
                    : 'bg-[#dafbe1] border border-[#54a668]'
                "
              >
                <div class="w-2 h-2 bg-[#3fb950] rounded-full" />
                <span class="text-xs" :class="isDark ? 'text-[#3fb950]' : 'text-[#1a7f37]'">
                  Online
                </span>
              </div>

              <div
                class="flex items-center gap-2 px-2.5 py-1 rounded-md border"
                :class="isDark ? 'bg-[#21262d] border-[#30363d]' : 'bg-[#f6f8fa] border-[#d0d7de]'"
              >
                <Activity
                  class="w-3.5 h-3.5"
                  :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
                />
                <span class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                  {{ currentTime }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <DataManagement :theme="theme" />
      </main>
    </div>
  </div>
</template>
