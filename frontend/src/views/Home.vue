<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import {
  BarChart3,
  TrendingUp,
  Database,
  Activity,
  Sun,
  Moon,
} from 'lucide-vue-next';

import PriceComparison from '../components/dashboard/PriceComparison.vue';
import ArbitrageOpportunities from '../components/dashboard/ArbitrageOpportunities.vue';
import DataManagement from '../components/dashboard/DataManagement.vue';

type TabType = 'comparison' | 'arbitrage' | 'management';
type Theme = 'light' | 'dark';

const activeTab = ref<TabType>('comparison');
const theme = ref<Theme>('dark');
const currentTime = ref(new Date().toLocaleTimeString('en-US'));
let timer: ReturnType<typeof setInterval> | null = null;

const toggleTheme = () => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark';
};

onMounted(() => {
  timer = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('en-US');
  }, 1000);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});

const isDark = computed(() => theme.value === 'dark');

const tabs: Array<{ id: TabType; label: string; icon: typeof BarChart3 }> = [
  { id: 'comparison', label: 'Price Comparison', icon: BarChart3 },
  { id: 'arbitrage', label: 'Arbitrage Opportunities', icon: TrendingUp },
  { id: 'management', label: 'Data Management', icon: Database },
];
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
                <h1 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                  Crypto Arbitrage System
                </h1>
                <p
                  class="text-xs"
                  :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
                >
                  Analysis Platform v2.0
                </p>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <button
                type="button"
                @click="toggleTheme"
                :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
                :class="[
                  'p-2 rounded-md transition-colors border',
                  isDark
                    ? 'bg-[#21262d] border-[#30363d] text-[#7d8590] hover:text-[#e6edf3] hover:border-[#58a6ff]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#57606a] hover:text-[#24292f] hover:border-[#0969da]',
                ]"
              >
                <component :is="isDark ? Sun : Moon" class="w-4 h-4" />
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

      <div
        :class="[
          'border-b',
          isDark ? 'bg-[#0d1117] border-[#21262d]' : 'bg-[#f6f8fa] border-[#d0d7de]',
        ]"
      >
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav class="flex gap-2">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              type="button"
              class="flex items-center gap-2 py-3 px-4 border-b-2 transition-colors text-sm"
              :class="[
                activeTab === tab.id
                  ? isDark
                    ? 'border-[#f78166] text-[#e6edf3]'
                    : 'border-[#fd8c73] text-[#24292f]'
                  : isDark
                    ? 'border-transparent text-[#7d8590] hover:text-[#e6edf3] hover:border-[#6e7681]'
                    : 'border-transparent text-[#57606a] hover:text-[#24292f] hover:border-[#d0d7de]',
              ]"
              @click="activeTab = tab.id"
            >
              <component :is="tab.icon" class="w-4 h-4" />
              {{ tab.label }}
            </button>
          </nav>
        </div>
      </div>

      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <PriceComparison v-if="activeTab === 'comparison'" :theme="theme" />
        <ArbitrageOpportunities v-else-if="activeTab === 'arbitrage'" :theme="theme" />
        <DataManagement v-else :theme="theme" />
      </main>
    </div>
  </div>
</template>
