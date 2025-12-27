<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { theme as antdTheme } from 'ant-design-vue';
import { Moon, Sun } from 'lucide-vue-next';
import {
  BarChartOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  LineChartOutlined,
  PlayCircleOutlined,
  ProfileOutlined,
} from '@ant-design/icons-vue';
import { getThemeMode, isDarkMode, setThemeMode } from '../utils/theme';

const route = useRoute();
const router = useRouter();

const collapsed = ref(false);

type Theme = 'light' | 'dark';
const darkModeState = ref(isDarkMode());
const isDark = computed(() => darkModeState.value);
const theme = computed<Theme>(() => (isDark.value ? 'dark' : 'light'));

const updateDarkModeState = () => {
  darkModeState.value = isDarkMode();
};

const toggleTheme = () => {
  const mode = getThemeMode();
  if (mode === 'auto') {
    setThemeMode(isDark.value ? 'light' : 'dark');
  } else {
    setThemeMode(mode === 'dark' ? 'light' : 'dark');
  }
  updateDarkModeState();
};

onMounted(() => {
  const observer = new MutationObserver(() => updateDarkModeState());
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  });
});

type MenuKey =
  | '/app/tasks'
  | '/app/batches'
  | '/app/opportunities'
  | '/app/reports'
  | '/app/templates';

const selectedKey = computed<MenuKey>(() => {
  const path = route.path;
  const candidates: MenuKey[] = [
    '/app/tasks',
    '/app/batches',
    '/app/opportunities',
    '/app/reports',
    '/app/templates',
  ];
  const match = candidates.find((k) => path === k || path.startsWith(`${k}/`));
  return match ?? '/app/opportunities';
});

const navigate = (key: string) => {
  router.push(key);
};

const onMenuClick = (e: any) => {
  navigate(String(e?.key ?? ''));
};

const goPriceComparison = () => router.push('/app/comparison');
const goRunTask = () => router.push('/app/templates');

const configTheme = computed(() => ({
  algorithm: isDark.value ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: isDark.value ? '#58a6ff' : '#0969da',
    colorLink: isDark.value ? '#58a6ff' : '#0969da',
    borderRadius: 6,
    colorBgLayout: isDark.value ? '#0d1117' : '#f6f8fa',
    colorBgContainer: isDark.value ? '#161b22' : '#ffffff',
    colorBorder: isDark.value ? '#30363d' : '#d0d7de',
  },
}));

const layoutClass = computed(() =>
  isDark.value ? 'bg-[#0d1117] text-[#e6edf3]' : 'bg-[#f6f8fa] text-[#24292f]',
);
const borderClass = computed(() => (isDark.value ? 'border-[#30363d]' : 'border-[#d0d7de]'));
const headerSubtleClass = computed(() => (isDark.value ? 'text-[#7d8590]' : 'text-[#57606a]'));

const secondaryButtonClass = computed(() =>
  isDark.value
    ? 'bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d]'
    : 'bg-white hover:bg-[#f6f8fa] text-[#24292f] border border-[#d0d7de]',
);
</script>

<template>
  <a-config-provider :theme="configTheme">
    <a-layout class="min-h-screen" :class="layoutClass">
      <a-layout-sider
        v-model:collapsed="collapsed"
        collapsible
        :collapsed-width="72"
        :width="240"
        :theme="isDark ? 'dark' : 'light'"
        :class="['border-r', borderClass, isDark ? 'bg-[#0d1117]' : 'bg-white']"
      >
        <div :class="['h-14 flex items-center px-4 gap-3 border-b', borderClass]">
          <div
            :class="[
              'w-8 h-8 rounded-md border flex items-center justify-center',
              borderClass,
              isDark ? 'bg-[#161b22]' : 'bg-[#f6f8fa]',
            ]"
          >
            <BarChartOutlined :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'" />
          </div>
          <div v-if="!collapsed" class="leading-tight">
            <div :class="['text-sm font-semibold', isDark ? 'text-[#e6edf3]' : 'text-[#24292f]']">Etrade</div>
            <div :class="['text-xs', headerSubtleClass]">CEX↔DEX 分析平台</div>
          </div>
        </div>

        <a-menu
          :selectedKeys="[selectedKey]"
          mode="inline"
          :theme="isDark ? 'dark' : 'light'"
          @click="onMenuClick"
          :class="['pt-2', isDark ? 'bg-[#0d1117]' : 'bg-white']"
        >
          <a-menu-item key="/app/tasks">
            <template #icon><ProfileOutlined /></template>
            任务
          </a-menu-item>
          <a-menu-item key="/app/batches">
            <template #icon><DatabaseOutlined /></template>
            批次
          </a-menu-item>
          <a-menu-item key="/app/opportunities">
            <template #icon><BarChartOutlined /></template>
            机会
          </a-menu-item>
          <a-menu-item key="/app/reports">
            <template #icon><FileTextOutlined /></template>
            报告
          </a-menu-item>
          <a-menu-item key="/app/templates">
            <template #icon><DatabaseOutlined /></template>
            模板
          </a-menu-item>
        </a-menu>
      </a-layout-sider>

      <a-layout :class="layoutClass">
        <a-layout-header
          :class="[
            'border-b flex items-center justify-between px-4',
            borderClass,
            isDark ? 'bg-[#0d1117]' : 'bg-white',
          ]"
          style="height: 56px; line-height: 56px"
        >
          <div class="text-sm" :class="headerSubtleClass">任务 → 批次 → 机会 → 详情 → 报告</div>
          <div class="flex items-center gap-3">
            <div class="text-xs" :class="headerSubtleClass">{{ route.meta?.title ?? route.name }}</div>
            <button
              type="button"
              class="px-3 py-1.5 rounded-md text-sm transition-colors inline-flex items-center gap-2"
              :class="secondaryButtonClass"
              @click="goPriceComparison"
              title="打开价格对比"
            >
              <LineChartOutlined />
              价格对比
            </button>
            <button
              type="button"
              class="px-3 py-1.5 rounded-md text-sm transition-colors inline-flex items-center gap-2"
              :class="secondaryButtonClass"
              @click="goRunTask"
              title="到模板页运行任务"
            >
              <PlayCircleOutlined />
              运行任务
            </button>
            <button
              type="button"
              class="px-3 py-1.5 rounded-md text-sm transition-colors inline-flex items-center gap-2"
              :class="secondaryButtonClass"
              @click="toggleTheme"
              :title="theme === 'dark' ? '切换为浅色' : '切换为深色'"
            >
              <component :is="theme === 'dark' ? Sun : Moon" class="w-4 h-4" />
              主题
            </button>
          </div>
        </a-layout-header>

        <a-layout-content :class="['p-4', isDark ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]']">
          <router-view />
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>
