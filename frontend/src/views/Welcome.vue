<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  ArrowRight,
  BarChart3,
  Blocks,
  FileText,
  GitBranch,
  ListChecks,
  Moon,
  Shield,
  Sun,
  Workflow,
} from 'lucide-vue-next';
import { getThemeMode, isDarkMode, setThemeMode } from '../utils/theme';

type Theme = 'light' | 'dark';

const router = useRouter();

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

const primaryButtonClass = computed(() =>
  isDark.value
    ? 'bg-[#238636] hover:bg-[#2ea043] text-white'
    : 'bg-[#1f883d] hover:bg-[#2da44e] text-white',
);

const secondaryButtonClass = computed(() =>
  isDark.value
    ? 'bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d]'
    : 'bg-white hover:bg-[#f6f8fa] text-[#24292f] border border-[#d0d7de]',
);

const surfaceClass = computed(() =>
  isDark.value ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]',
);

const subtleTextClass = computed(() => (isDark.value ? 'text-[#7d8590]' : 'text-[#57606a]'));
</script>

<template>
  <div :class="['min-h-screen', isDark ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]']">
    <header :class="['border-b', isDark ? 'border-[#21262d] bg-[#0d1117]' : 'border-[#d0d7de] bg-white']">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 rounded-lg flex items-center justify-center border"
            :class="isDark ? 'border-[#30363d] bg-[#161b22]' : 'border-[#d0d7de] bg-white'"
          >
            <BarChart3 class="w-5 h-5" :class="isDark ? 'text-[#3fb950]' : 'text-[#1a7f37]'" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-base font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Etrade</h1>
            </div>
            <p class="text-xs" :class="subtleTextClass">CEX ↔ DEX 历史套利分析平台</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-md text-sm transition-colors"
            :class="secondaryButtonClass"
            @click="toggleTheme"
            :title="theme === 'dark' ? '切换为浅色' : '切换为深色'"
          >
            <span class="inline-flex items-center gap-2">
              <component :is="theme === 'dark' ? Sun : Moon" class="w-4 h-4" />
              主题
            </span>
          </button>

          <button
            type="button"
            class="px-3 py-1.5 rounded-md text-sm transition-colors"
            :class="primaryButtonClass"
            @click="router.push('/app')"
          >
            <span class="inline-flex items-center gap-2">
              进入系统
              <ArrowRight class="w-4 h-4" />
            </span>
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
        <div class="space-y-6">
          <div class="space-y-3">
            <p class="text-sm" :class="subtleTextClass">Web 界面入口</p>
            <h2 class="text-3xl sm:text-4xl font-semibold leading-tight" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
              Etrade · CEX ↔ DEX 历史套利分析平台
            </h2>
            <p class="text-base leading-relaxed" :class="subtleTextClass">
              按 “任务 → 批次 → 机会 → 详情 → 报告” 的流程使用系统。下面给出一个最短操作路径。
            </p>
          </div>

          <div class="flex flex-wrap gap-3">
            <button type="button" class="px-4 py-2 rounded-md text-sm transition-colors" :class="primaryButtonClass" @click="router.push('/app/tasks')">
              <span class="inline-flex items-center gap-2">
                <ListChecks class="w-4 h-4" />
                打开任务中心
              </span>
            </button>
            <button type="button" class="px-4 py-2 rounded-md text-sm transition-colors" :class="secondaryButtonClass" @click="router.push('/app/opportunities')">
              <span class="inline-flex items-center gap-2">
                <BarChart3 class="w-4 h-4" />
                查看机会仪表盘
              </span>
            </button>
            <button type="button" class="px-4 py-2 rounded-md text-sm transition-colors" :class="secondaryButtonClass" @click="router.push('/app/comparison')">
              <span class="inline-flex items-center gap-2">
                <GitBranch class="w-4 h-4" />
                价格对比
              </span>
            </button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="rounded-lg border p-4" :class="surfaceClass">
              <div class="flex items-center gap-2 mb-2">
                <Workflow class="w-4 h-4" :class="isDark ? 'text-[#3fb950]' : 'text-[#1a7f37]'" />
                <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">快速开始</div>
              </div>
              <div class="text-xs leading-relaxed" :class="subtleTextClass">
                1) 到「模板」创建/选择 `analyse` 模板<br />
                2) 运行模板生成任务（或在「机会」里创建实验并运行）<br />
                3) 到「批次」打开批次，在「机会」查看图表与表格<br />
                4) 在「报告」提交生成并下载
              </div>
            </div>
            <div class="rounded-lg border p-4" :class="surfaceClass">
              <div class="flex items-center gap-2 mb-2">
                <Shield class="w-4 h-4" :class="isDark ? 'text-[#d29922]' : 'text-[#9a6700]'" />
                <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">机会详情</div>
              </div>
              <div class="text-xs leading-relaxed" :class="subtleTextClass">
                在「机会」页点击一条记录可打开详情：查看 risk_score / volatility / slippage，以及 block_time 附近的价格上下文。
              </div>
            </div>
          </div>
        </div>

        <div class="relative">
          <div
            class="absolute inset-0 blur-3xl opacity-30 rounded-3xl"
            :class="isDark ? 'bg-gradient-to-br from-[#58a6ff] via-[#f78166] to-[#3fb950]' : 'bg-gradient-to-br from-[#0969da] via-[#fb8f44] to-[#1a7f37]'"
          />
          <div class="relative rounded-2xl border overflow-hidden" :class="surfaceClass">
            <div class="p-5 border-b flex items-center justify-between" :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'">
              <div>
                <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">系统组成</div>
                <div class="text-xs" :class="subtleTextClass">Control Plane / Data Plane 拆分</div>
              </div>
              <Blocks class="w-5 h-5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
            </div>
            <div class="p-5">
              <div class="grid grid-cols-1 gap-3 text-sm">
                <div class="rounded-lg border p-4 flex items-start justify-between gap-3" :class="surfaceClass">
                  <div>
                    <div class="font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Vue 前端</div>
                    <div class="text-xs mt-1" :class="subtleTextClass">任务中心 / 批次 / 图表 / 报告</div>
                  </div>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="isDark ? 'bg-[#1f6feb]/15 text-[#58a6ff]' : 'bg-[#ddf4ff] text-[#0969da]'">UI</span>
                </div>
                <div class="rounded-lg border p-4 flex items-start justify-between gap-3" :class="surfaceClass">
                  <div>
                    <div class="font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Go API (Gin)</div>
                    <div class="text-xs mt-1" :class="subtleTextClass">REST + Swagger / 模板 / 调度</div>
                  </div>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="isDark ? 'bg-[#238636]/15 text-[#3fb950]' : 'bg-[#dafbe1] text-[#1a7f37]'">Control</span>
                </div>
                <div class="rounded-lg border p-4 flex items-start justify-between gap-3" :class="surfaceClass">
                  <div>
                    <div class="font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Python Worker (gRPC)</div>
                    <div class="text-xs mt-1" :class="subtleTextClass">采集 / 聚合 / 分析 / 风险模型</div>
                  </div>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="isDark ? 'bg-[#f78166]/15 text-[#f78166]' : 'bg-[#ffebe9] text-[#cf222e]'">Data</span>
                </div>
                <div class="rounded-lg border p-4 flex items-start justify-between gap-3" :class="surfaceClass">
                  <div>
                    <div class="font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">PostgreSQL</div>
                    <div class="text-xs mt-1" :class="subtleTextClass">tasks / logs / batches / opportunities</div>
                  </div>
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="isDark ? 'bg-[#21262d] text-[#7d8590]' : 'bg-[#f6f8fa] text-[#57606a]'">DB</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="rounded-xl border p-5" :class="surfaceClass">
          <div class="flex items-center gap-2 mb-2">
            <BarChart3 class="w-4 h-4" :class="isDark ? 'text-[#58a6ff]' : 'text-[#0969da]'" />
            <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">机会页（Dashboard）</div>
          </div>
          <div class="text-xs leading-relaxed" :class="subtleTextClass">查看 KPI + 图表 + 表格；支持多批次对比与导出图表 PNG。</div>
        </div>
        <div class="rounded-xl border p-5" :class="surfaceClass">
          <div class="flex items-center gap-2 mb-2">
            <ListChecks class="w-4 h-4" :class="isDark ? 'text-[#3fb950]' : 'text-[#1a7f37]'" />
            <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">任务中心</div>
          </div>
          <div class="text-xs leading-relaxed" :class="subtleTextClass">查看任务状态与日志；必要时可取消任务。</div>
        </div>
        <div class="rounded-xl border p-5" :class="surfaceClass">
          <div class="flex items-center gap-2 mb-2">
            <FileText class="w-4 h-4" :class="isDark ? 'text-[#d29922]' : 'text-[#9a6700]'" />
            <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">报告</div>
          </div>
          <div class="text-xs leading-relaxed" :class="subtleTextClass">对指定批次提交报告生成任务，并下载文件。</div>
        </div>
      </section>
    </main>

    <footer class="border-t" :class="isDark ? 'border-[#21262d] text-[#7d8590]' : 'border-[#d0d7de] text-[#57606a]'">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-xs flex flex-wrap items-center justify-between gap-2">
        <div>© {{ new Date().getFullYear() }} Etrade</div>
        <div class="flex items-center gap-4">
          <button type="button" class="hover:underline" @click="router.push('/app/templates')">模板</button>
          <button type="button" class="hover:underline" @click="router.push('/app/batches')">批次</button>
          <button type="button" class="hover:underline" @click="router.push('/app/reports')">报告</button>
        </div>
      </div>
    </footer>
  </div>
</template>
