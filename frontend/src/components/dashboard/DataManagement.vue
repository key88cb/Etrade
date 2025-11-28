<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
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
import api from '@/api';

type Theme = 'light' | 'dark';
type TaskStatus = 'idle' | 'running' | 'success' | 'error';
type TaskIcon = 'download' | 'database' | 'trending';
type PipelineTaskType = 'collect_binance' | 'collect_uniswap' | 'process_prices' | 'analyse';

interface Props {
  theme: Theme;
}

interface Task {
  id: string;
  name: string;
  description: string;
  icon: TaskIcon;
  status: TaskStatus;
  taskType: PipelineTaskType;
  lastRun?: string;
  duration?: string;
}

interface TemplateConfigs {
  collect_binance: {
    csv_path: string;
    import_percentage: number;
    chunk_size: number;
  };
  collect_uniswap: {
    pool_address: string;
    start_date: string;
    end_date: string;
  };
  process_prices: {
    start_date: string;
    end_date: string;
    aggregation_interval: string;
    overwrite: boolean;
  };
  analyse: {
    batch_id: string;
    overwrite: boolean;
    window_start: string;
    window_end: string;
    strategy: {
      profit_threshold: number;
      time_delay_seconds: number;
      initial_investment: number;
    };
  };
}

const props = defineProps<Props>();
const remoteTasks = ref<any[]>([]);
const templates = ref<any[]>([]);
const reportForm = ref({
  batch_id: '',
  format: 'PDF',
  template_id: '',
});
const controlError = ref('');
const runningTemplateId = ref<number | null>(null);

const templateConfigs = reactive<TemplateConfigs>({
  collect_binance: {
    csv_path: '/data/binance_aggTrades_ETHUSDT.csv',
    import_percentage: 100,
    chunk_size: 1000000,
  },
  collect_uniswap: {
    pool_address: '0x...',
    start_date: '',
    end_date: '',
  },
  process_prices: {
    start_date: '',
    end_date: '',
    aggregation_interval: '5m',
    overwrite: true,
  },
  analyse: {
    batch_id: '',
    overwrite: false,
    window_start: '',
    window_end: '',
    strategy: {
      profit_threshold: 0.5,
      time_delay_seconds: 15,
      initial_investment: 100000,
    },
  },
});

const tasks = ref<Task[]>([
  {
    id: 'collect-binance',
    taskType: 'collect_binance',
    name: 'Binance 数据导入',
    description: 'Import Binance historical trades from CSV',
    icon: 'download',
    status: 'idle',
  },
  {
    id: 'collect-uniswap',
    taskType: 'collect_uniswap',
    name: 'Uniswap 数据采集',
    description: 'Fetch Uniswap V3 swap data via The Graph API',
    icon: 'download',
    status: 'idle',
  },
  {
    id: 'process-prices',
    taskType: 'process_prices',
    name: '价格聚合',
    description: 'Aggregate raw market data into regular intervals',
    icon: 'database',
    status: 'idle',
  },
  {
    id: 'analyse',
    taskType: 'analyse',
    name: '套利分析',
    description: 'Detect arbitrage windows and compute metrics',
    icon: 'trending',
    status: 'idle',
  },
]);

const isDark = computed(() => props.theme === 'dark');
const labelTextClass = computed(() => (isDark.value ? 'text-[#e6edf3]' : 'text-[#24292f]'));

const iconMap: Record<TaskIcon, any> = {
  download: Download,
  database: Database,
  trending: TrendingUp,
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

const toUnixSeconds = (value: string) => {
  if (!value) return undefined;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return undefined;
  return Math.floor(parsed / 1000);
};

const toISODateTime = (value: string) => {
  if (!value) return undefined;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return undefined;
  return new Date(parsed).toISOString();
};

const buildOverrides = (taskType: PipelineTaskType): Record<string, unknown> => {
  switch (taskType) {
    case 'collect_binance':
      return { ...templateConfigs.collect_binance };
    case 'collect_uniswap': {
      const { pool_address, start_date, end_date } = templateConfigs.collect_uniswap;
      const overrides: Record<string, unknown> = { pool_address };
      const startTs = toUnixSeconds(start_date);
      if (typeof startTs === 'number') overrides.start_ts = startTs;
      const endTs = toUnixSeconds(end_date);
      if (typeof endTs === 'number') overrides.end_ts = endTs;
      return overrides;
    }
    case 'process_prices':
      return { ...templateConfigs.process_prices };
    case 'analyse': {
      const { batch_id, overwrite, window_start, window_end, strategy } = templateConfigs.analyse;
      const overrides: Record<string, unknown> = {
        overwrite,
        strategy: { ...strategy },
      };
      if (batch_id !== '') {
        const parsed = Number(batch_id);
        if (!Number.isNaN(parsed) && parsed > 0) {
          overrides.batch_id = parsed;
        }
      }
      const startISO = toISODateTime(window_start);
      if (startISO) overrides.start = startISO;
      const endISO = toISODateTime(window_end);
      if (endISO) overrides.end = endISO;
      return overrides;
    }
    default:
      return {};
  }
};

const updateTaskState = (taskType: PipelineTaskType, payload: Partial<Task>) => {
  tasks.value = tasks.value.map((task) =>
    task.taskType === taskType ? { ...task, ...payload } : task,
  );
};

const fetchControlData = async () => {
  controlError.value = '';
  try {
    const [taskRes, templateRes] = await Promise.all([
      api.getTasks({ page: 1, limit: 5 }),
      api.getTemplates(),
    ]);
    remoteTasks.value = taskRes.data?.data?.items ?? [];
    templates.value = templateRes.data?.data ?? templateRes.data ?? [];
  } catch (error: any) {
    controlError.value = error?.message ?? '控制中心数据加载失败';
  }
};

const baseInputClass =
  'w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-xs focus:border-transparent';
const darkInputClass =
  'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]';
const lightInputClass =
  'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]';

const runTemplateQuick = async (id: number) => {
  runningTemplateId.value = id;
  controlError.value = '';
  try {
    await api.runTemplate(id, {});
    await fetchControlData();
  } catch (error: any) {
    controlError.value = error?.message ?? '运行模板失败';
  } finally {
    runningTemplateId.value = null;
  }
};

const submitQuickReport = async () => {
  if (!reportForm.value.batch_id) {
    controlError.value = '请选择批次 ID';
    return;
  }
  try {
    await api.createReport({
      batch_id: Number(reportForm.value.batch_id),
      template_id: reportForm.value.template_id ? Number(reportForm.value.template_id) : undefined,
      format: reportForm.value.format,
    });
    reportForm.value.batch_id = '';
    reportForm.value.template_id = '';
    reportForm.value.format = 'PDF';
    await fetchControlData();
  } catch (error: any) {
    controlError.value = error?.message ?? '生成报告失败';
  }
};

onMounted(fetchControlData);

const runPipelineTask = async (taskType: PipelineTaskType) => {
  controlError.value = '';
  const template = templates.value.find((tpl) => tpl.task_type === taskType);
  if (!template) {
    controlError.value = `未找到 ${taskType} 类型的模板，请先在模板管理中创建。`;
    return;
  }
  updateTaskState(taskType, { status: 'running' });
  try {
    const overrides = buildOverrides(taskType);
    await api.runTemplate(template.id, { overrides });
    updateTaskState(taskType, {
      status: 'success',
      lastRun: new Date().toLocaleString('en-US'),
    });
    await fetchControlData();
  } catch (error: any) {
    controlError.value = error?.message ?? '任务运行失败';
    updateTaskState(taskType, { status: 'error' });
  }
};
</script>

<template>
  <div class="space-y-4">
    <div
      class="rounded-md border p-4 space-y-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex items-center gap-2">
        <Play class="w-4 h-4" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
        <h2 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">任务控制中心</h2>
      </div>
      <p v-if="controlError" class="text-xs text-[#f85149]">{{ controlError }}</p>
      <div class="space-y-3">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="border rounded-md p-3 transition-colors"
          :class="isDark ? 'border-[#30363d] hover:border-[#58a6ff] bg-[#0d1117]' : 'border-[#d0d7de] hover:border-[#0969da] bg-[#f6f8fa]'"
        >
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
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
                  class="flex flex-wrap gap-3 mt-1.5 text-xs"
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
                @click="runPipelineTask(task.taskType)"
              >
                <Play class="w-3 h-3" />
                Run
              </button>
            </div>
          </div>

          <div
            class="mt-3 pt-3 border-t"
            :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'"
          >
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <template v-if="task.taskType === 'collect_binance'">
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>CSV Path</span>
                  <input
                    v-model="templateConfigs.collect_binance.csv_path"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Import %</span>
                  <input
                    type="number"
                    v-model.number="templateConfigs.collect_binance.import_percentage"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Chunk Size</span>
                  <input
                    type="number"
                    v-model.number="templateConfigs.collect_binance.chunk_size"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
              </template>

              <template v-else-if="task.taskType === 'collect_uniswap'">
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Pool Address</span>
                  <input
                    v-model="templateConfigs.collect_uniswap.pool_address"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Start Date</span>
                  <input
                    type="date"
                    v-model="templateConfigs.collect_uniswap.start_date"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>End Date</span>
                  <input
                    type="date"
                    v-model="templateConfigs.collect_uniswap.end_date"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
              </template>

              <template v-else-if="task.taskType === 'process_prices'">
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Start Date</span>
                  <input
                    type="date"
                    v-model="templateConfigs.process_prices.start_date"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>End Date</span>
                  <input
                    type="date"
                    v-model="templateConfigs.process_prices.end_date"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Interval</span>
                  <select
                    v-model="templateConfigs.process_prices.aggregation_interval"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  >
                    <option value="1m">1m</option>
                    <option value="5m">5m</option>
                    <option value="15m">15m</option>
                    <option value="1h">1h</option>
                  </select>
                </label>
                <label :class="[labelTextClass, 'flex items-center gap-2']">
                  <input
                    type="checkbox"
                    v-model="templateConfigs.process_prices.overwrite"
                  />
                  覆盖旧数据
                </label>
              </template>

              <template v-else>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Batch ID（可选）</span>
                  <input
                    type="text"
                    inputmode="numeric"
                    placeholder="留空自动创建批次"
                    v-model="templateConfigs.analyse.batch_id"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex items-center gap-2']">
                  <input
                    type="checkbox"
                    v-model="templateConfigs.analyse.overwrite"
                  />
                  覆盖批次
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>分析开始时间</span>
                  <input
                    type="datetime-local"
                    v-model="templateConfigs.analyse.window_start"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>分析结束时间</span>
                  <input
                    type="datetime-local"
                    v-model="templateConfigs.analyse.window_end"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Profit Threshold</span>
                  <input
                    type="number"
                    v-model.number="templateConfigs.analyse.strategy.profit_threshold"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Time Delay (s)</span>
                  <input
                    type="number"
                    v-model.number="templateConfigs.analyse.strategy.time_delay_seconds"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
                <label :class="[labelTextClass, 'flex flex-col gap-1']">
                  <span>Investment (USDT)</span>
                  <input
                    type="number"
                    v-model.number="templateConfigs.analyse.strategy.initial_investment"
                    :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
                  />
                </label>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex items-center justify-between mb-4">
        <h2 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Latest Tasks</h2>
        <button class="text-xs" :class="isDark ? 'text-[#58a6ff]' : 'text-[#0969da]'" @click="fetchControlData">
          Refresh
        </button>
      </div>
      <div class="space-y-2">
        <div
          v-for="task in remoteTasks"
          :key="task.task_id"
          class="border rounded px-3 py-2 flex items-center justify-between"
          :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'"
        >
          <div>
            <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ task.type }}</div>
            <div class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">ID: {{ task.task_id }}</div>
          </div>
          <span class="text-xs px-2 py-1 rounded border" :class="task.status === 'SUCCESS' ? (isDark ? 'border-[#3fb950] text-[#3fb950]' : 'border-[#1a7f37] text-[#1a7f37]') : 'border-[#7d8590] text-[#7d8590]'">
            {{ task.status }}
          </span>
        </div>
        <div v-if="remoteTasks.length === 0" class="text-xs text-[#7d8590]">暂无远程任务，请稍后刷新。</div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        class="rounded-md border p-4 space-y-3"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center justify-between">
          <h3 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Template Quick Actions</h3>
          <button class="text-xs" :class="isDark ? 'text-[#58a6ff]' : 'text-[#0969da]'" @click="fetchControlData">
            Reload
          </button>
        </div>
        <div v-if="templates.length === 0" class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
          暂无模板，前往模板管理创建。
        </div>
        <div
          v-for="template in templates.slice(0, 4)"
          :key="template.id"
          class="border rounded px-3 py-2 flex items-center justify-between"
          :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'"
        >
          <div>
            <div class="text-sm font-medium">{{ template.name }}</div>
            <div class="text-xs text-[#7d8590] font-mono">{{ template.task_type }}</div>
          </div>
          <button
            type="button"
            class="text-xs px-2 py-1 rounded"
            :class="isDark ? 'bg-[#21262d] text-[#e6edf3]' : 'bg-[#f6f8fa] text-[#24292f]'"
            :disabled="runningTemplateId === template.id"
            @click="runTemplateQuick(template.id)"
          >
            {{ runningTemplateId === template.id ? '运行中…' : '运行' }}
          </button>
        </div>
      </div>

      <div
        class="rounded-md border p-4 space-y-3"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center justify-between">
          <div>
            <h3 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Quick Report</h3>
            <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              直接在此创建报告任务，详细批次数据请前往 Arbitrage 页查看。
            </p>
          </div>
          <button class="text-xs" :class="isDark ? 'text-[#58a6ff]' : 'text-[#0969da]'" @click="fetchControlData">
            Reload
          </button>
        </div>
        <div class="grid grid-cols-1 gap-2 text-xs">
          <input
            v-model="reportForm.batch_id"
            type="number"
            placeholder="Batch ID"
            :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
          />
          <input
            v-model="reportForm.template_id"
            type="number"
            placeholder="Template ID (optional)"
            :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
          />
          <select
            v-model="reportForm.format"
            :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"
          >
            <option value="PDF">PDF</option>
            <option value="HTML">HTML</option>
            <option value="Markdown">Markdown</option>
          </select>
        </div>
        <button
          type="button"
          class="w-full px-3 py-1.5 bg-[#238636] text-white text-xs rounded hover:bg-[#2ea043]"
          @click="submitQuickReport"
        >
          Submit Report Task
        </button>
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
