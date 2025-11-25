<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  Download,
  Database,
  TrendingUp,
  Play,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Terminal,
} from 'lucide-vue-next';

type Theme = 'light' | 'dark';
type TaskStatus = 'idle' | 'running' | 'success' | 'error';
type TaskIcon = 'download' | 'database' | 'trending';

interface Props {
  theme: Theme;
}

interface Task {
  id: string;
  name: string;
  description: string;
  icon: TaskIcon;
  status: TaskStatus;
  lastRun?: string;
  duration?: string;
}

const props = defineProps<Props>();

const tasks = ref<Task[]>([
  {
    id: 'uniswap-ingest',
    name: 'Uniswap Data Ingestion',
    description: 'Fetch Uniswap V3 swap data via The Graph API',
    icon: 'download',
    status: 'idle',
  },
  {
    id: 'binance-ingest',
    name: 'Binance Data Import',
    description: 'Import Binance historical trades from CSV',
    icon: 'download',
    status: 'idle',
  },
  {
    id: 'aggregate',
    name: 'Data Aggregation',
    description: 'Aggregate raw data by time intervals',
    icon: 'database',
    status: 'idle',
  },
  {
    id: 'analyze',
    name: 'Arbitrage Analysis',
    description: 'Detect arbitrage opportunities and calculate profits',
    icon: 'trending',
    status: 'idle',
  },
]);

const config = ref({
  startTimestamp: '1725148800',
  endTimestamp: '1727740800',
  poolAddress: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640',
  csvPath: '/data/binance_aggTrades_ETHUSDT.csv',
  aggregationInterval: '5m',
  timeDelay: '15',
  profitThreshold: '0.5',
});

const isDark = computed(() => props.theme === 'dark');

const iconMap: Record<TaskIcon, any> = {
  download: Download,
  database: Database,
  trending: TrendingUp,
};

const runTask = async (taskId: string) => {
  tasks.value = tasks.value.map((task) =>
    task.id === taskId ? { ...task, status: 'running' } : task,
  );

  await new Promise((resolve) => setTimeout(resolve, 2000 + Math.random() * 2000));

  const success = Math.random() > 0.1;
  tasks.value = tasks.value.map((task) =>
    task.id === taskId
      ? {
          ...task,
          status: success ? 'success' : 'error',
          lastRun: new Date().toLocaleString('en-US'),
          duration: `${(2 + Math.random() * 3).toFixed(1)}s`,
        }
      : task,
  );
};

const statusLabel = (status: TaskStatus) => {
  switch (status) {
    case 'running':
      return 'Running';
    case 'success':
      return 'Success';
    case 'error':
      return 'Error';
    default:
      return 'Ready';
  }
};

const statusAccent = (status: TaskStatus) => {
  switch (status) {
    case 'success':
      return isDark.value
        ? 'bg-[#26a64126] text-[#3fb950] border border-[#3fb950]'
        : 'bg-[#dafbe1] text-[#1a7f37] border border-[#1a7f37]';
    case 'error':
      return isDark.value
        ? 'bg-[#f8514926] text-[#f85149] border border-[#f85149]'
        : 'bg-[#ffebe9] text-[#cf222e] border border-[#cf222e]';
    case 'running':
      return isDark.value
        ? 'bg-[#388bfd26] text-[#58a6ff] border border-[#58a6ff]'
        : 'bg-[#ddf4ff] text-[#0969da] border border-[#0969da]';
    default:
      return isDark.value
        ? 'bg-[#21262d] text-[#7d8590] border border-[#30363d]'
        : 'bg-[#f6f8fa] text-[#57606a] border border-[#d0d7de]';
  }
};

const statusIcon = (status: TaskStatus) => {
  if (status === 'running') return Loader2;
  if (status === 'success') return CheckCircle2;
  if (status === 'error') return AlertCircle;
  return null;
};
</script>

<template>
  <div class="space-y-4">
    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex items-center gap-2 mb-4">
        <Terminal class="w-4 h-4" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
        <h2 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Configuration Parameters</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-3">
          <h3
            class="text-xs mb-3 pb-2 border-b"
            :class="isDark ? 'text-[#7d8590] border-[#21262d]' : 'text-[#57606a] border-[#d0d7de]'"
          >
            Data Ingestion
          </h3>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              Start Timestamp (Unix seconds)
            </label>
            <input
              v-model="config.startTimestamp"
              type="text"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
            <p class="text-xs mt-1" :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'">
              2025-09-01 00:00:00
            </p>
          </div>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              End Timestamp (Unix seconds)
            </label>
            <input
              v-model="config.endTimestamp"
              type="text"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
            <p class="text-xs mt-1" :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'">
              2025-09-30 23:59:59
            </p>
          </div>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              Pool Address
            </label>
            <input
              v-model="config.poolAddress"
              type="text"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-xs font-mono focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
            <p class="text-xs mt-1" :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'">
              Uniswap V3 USDT/ETH Pool
            </p>
          </div>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              CSV Path
            </label>
            <input
              v-model="config.csvPath"
              type="text"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
          </div>
        </div>

        <div class="space-y-3">
          <h3
            class="text-xs mb-3 pb-2 border-b"
            :class="isDark ? 'text-[#7d8590] border-[#21262d]' : 'text-[#57606a] border-[#d0d7de]'"
          >
            Analysis Parameters
          </h3>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              Aggregation Interval
            </label>
            <select
              v-model="config.aggregationInterval"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            >
              <option value="1m">1 Minute</option>
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="1h">1 Hour</option>
            </select>
          </div>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              Time Delay (seconds)
            </label>
            <input
              v-model="config.timeDelay"
              type="number"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
            <p class="text-xs mt-1" :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'">
              DEX to CEX price match delay
            </p>
          </div>

          <div>
            <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              Profit Threshold (USDT)
            </label>
            <input
              v-model="config.profitThreshold"
              type="number"
              step="0.1"
              class="w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
            <p class="text-xs mt-1" :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'">
              Minimum net profit to record
            </p>
          </div>

          <div
            class="border rounded-md p-3 mt-3"
            :class="isDark ? 'bg-[#d2992214] border-[#9e6a03]' : 'bg-[#fff8c5] border-[#d4a72c]'"
          >
            <div class="flex items-start gap-2">
              <AlertCircle class="w-4 h-4 text-[#d29922] mt-0.5 flex-shrink-0" />
              <p class="text-xs" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                Recommended: Execute tasks in sequence (INGEST → AGGREGATE → ANALYZE)
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex items-center gap-2 mb-4">
        <Play class="w-4 h-4" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
        <h2 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Task Execution</h2>
      </div>

      <div class="space-y-2">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="border rounded-md p-3 transition-colors"
          :class="isDark ? 'border-[#30363d] hover:border-[#58a6ff] bg-[#0d1117]' : 'border-[#d0d7de] hover:border-[#0969da] bg-[#f6f8fa]'"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3 flex-1">
              <div
                class="w-10 h-10 rounded flex items-center justify-center"
                :class="{
                  'bg-[#26a64126] text-[#3fb950]': task.status === 'success' && isDark,
                  'bg-[#dafbe1] text-[#1a7f37]': task.status === 'success' && !isDark,
                  'bg-[#f8514926] text-[#f85149]': task.status === 'error' && isDark,
                  'bg-[#ffebe9] text-[#cf222e]': task.status === 'error' && !isDark,
                  'bg-[#388bfd26] text-[#58a6ff]': task.status === 'running' && isDark,
                  'bg-[#ddf4ff] text-[#0969da]': task.status === 'running' && !isDark,
                  'bg-[#21262d] text-[#7d8590]': task.status === 'idle' && isDark,
                  'bg-[#eaeef2] text-[#57606a]': task.status === 'idle' && !isDark,
                }"
              >
                <component :is="iconMap[task.icon]" class="w-4 h-4" />
              </div>

              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="text-sm" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                    {{ task.name }}
                  </h3>
                  <component
                    v-if="statusIcon(task.status)"
                    :is="statusIcon(task.status)"
                    class="w-4 h-4"
                    :class="{
                      'text-[#58a6ff] animate-spin': task.status === 'running',
                      'text-[#3fb950]': task.status === 'success',
                      'text-[#f85149]': task.status === 'error',
                    }"
                  />
                </div>
                <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                  {{ task.description }}
                </p>
                <div
                  v-if="task.lastRun"
                  class="flex items-center gap-3 mt-1.5 text-xs"
                  :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'"
                >
                  <span>Last run: {{ task.lastRun }}</span>
                  <span v-if="task.duration">Duration: {{ task.duration }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-1 rounded" :class="statusAccent(task.status)">
                {{ statusLabel(task.status) }}
              </span>
              <button
                type="button"
                class="px-3 py-1.5 bg-[#238636] text-white rounded text-sm hover:bg-[#2ea043] transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5"
                :disabled="task.status === 'running'"
                @click="runTask(task.id)"
              >
                <Play class="w-3 h-3" />
                Run
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div
        class="rounded-md border p-3"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center gap-3">
          <div :class="isDark ? 'bg-[#26a64126]' : 'bg-[#dafbe1]'" class="w-10 h-10 rounded flex items-center justify-center">
            <CheckCircle2 class="w-5 h-5 text-[#3fb950]" />
          </div>
          <div>
            <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">Database Status</p>
            <p :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Connected</p>
          </div>
        </div>
      </div>

      <div
        class="rounded-md border p-3"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center gap-3">
          <div :class="isDark ? 'bg-[#388bfd26]' : 'bg-[#ddf4ff]'" class="w-10 h-10 rounded flex items-center justify-center">
            <Database class="w-5 h-5 text-[#58a6ff]" />
          </div>
          <div>
            <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">Raw Records</p>
            <p :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">12,547</p>
          </div>
        </div>
      </div>

      <div
        class="rounded-md border p-3"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center gap-3">
          <div :class="isDark ? 'bg-[#6e40c926]' : 'bg-[#fbefff]'" class="w-10 h-10 rounded flex items-center justify-center">
            <TrendingUp class="w-5 h-5 text-[#bc8cff]" />
          </div>
          <div>
            <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">Opportunities</p>
            <p :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">47</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
