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
  FileText,
  Plus,
  Trash2,
  FileDown,
  X 
} from 'lucide-vue-next';
// 确保引入 backendURL
import api, { backendURL } from '../../api';

type Theme = 'light' | 'dark';
type TaskStatus = 'idle' | 'running' | 'success' | 'error';
type TaskIcon = 'download' | 'database' | 'trending';
type PipelineTaskType = 'collect_binance' | 'collect_uniswap' | 'process_prices' | 'analyse';
type ReportFormat = 'PDF' | 'HTML' | 'Markdown';

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

interface Batch {
  id: number;
  name: string;
}

interface Template {
  id: number;
  name: string;
  task_type: string;
}

interface Report {
  id: number;
  batch_id: number;
  template_id: number;
  format: string;
  status: string; 
  file_url: string;
  file_path: string;
  created_at: string;
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
    strategy: {
      profit_threshold: number;
      time_delay_seconds: number;
      initial_investment: number;
      start: string;
      end: string;
    };
  };
}

const props = defineProps<Props>();
const isDark = computed(() => props.theme === 'dark');

const remoteTasks = ref<any[]>([]);
const templates = ref<Template[]>([]);
const batches = ref<Batch[]>([]);
const reports = ref<Report[]>([]);

const isLoadingControl = ref(false);
const isLoadingReports = ref(false);
const isGeneratingReport = ref(false);
const controlError = ref('');
const showReportModal = ref(false);

const reportForm = reactive({
  batch_id: '' as string | number,
  template_id: '' as string | number,
  format: 'PDF' as ReportFormat,
  notes: '' 
});

const legacyReportForm = ref({
  batch_id: '',
  format: 'PDF',
  template_id: '',
});

const templateConfigs = reactive<TemplateConfigs>({
  collect_binance: { csv_path: '/data/binance_aggTrades_ETHUSDT.csv', import_percentage: 100, chunk_size: 1000000 },
  collect_uniswap: { pool_address: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640', start_date: '', end_date: '' },
  process_prices: { start_date: '', end_date: '', aggregation_interval: '5m', overwrite: true },
  analyse: { batch_id: '', overwrite: false, strategy: { profit_threshold: 0.5, time_delay_seconds: 15, initial_investment: 10000, start: '', end: '' } },
});

const tasks = ref<Task[]>([
  { id: 'collect-binance', taskType: 'collect_binance', name: 'Binance Import', description: 'Import historical data', icon: 'download', status: 'idle' },
  { id: 'collect-uniswap', taskType: 'collect_uniswap', name: 'Uniswap Fetch', description: 'Fetch on-chain data', icon: 'download', status: 'idle' },
  { id: 'process-prices', taskType: 'process_prices', name: 'Price Aggregation', description: 'Aggregate raw market data', icon: 'database', status: 'idle' },
  { id: 'analyse', taskType: 'analyse', name: 'Arbitrage Analysis', description: 'Detect arbitrage windows', icon: 'trending', status: 'idle' },
]);

const labelTextClass = computed(() => (isDark.value ? 'text-[#e6edf3]' : 'text-[#24292f]'));
const baseInputClass = 'w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-xs focus:border-transparent transition-all';
const darkInputClass = 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]';
const lightInputClass = 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]';

const iconMap: Record<TaskIcon, any> = { download: Download, database: Database, trending: TrendingUp };

const statusLabel = (status: string) => {
  if (!status) return 'Unknown';
  switch (status.toUpperCase()) {
    case 'RUNNING': case 'GENERATING': return 'Running';
    case 'SUCCESS': return 'Success';
    case 'ERROR': case 'FAILED': return 'Error';
    case 'PENDING': return 'Pending';
    default: return status;
  }
};

const statusAccent = (status: string) => {
  if (!status) return '';
  const s = status.toUpperCase();
  if (s === 'SUCCESS') return isDark.value ? 'bg-[#238636]/20 text-[#3fb950] border border-[#3fb950]/30' : 'bg-[#dafbe1] text-[#1a7f37] border border-[#1a7f37]/30';
  if (s === 'ERROR' || s === 'FAILED') return isDark.value ? 'bg-[#da3633]/20 text-[#f85149] border border-[#f85149]/30' : 'bg-[#ffebe9] text-[#cf222e] border border-[#cf222e]/30';
  if (s === 'RUNNING' || s === 'GENERATING') return isDark.value ? 'bg-[#1f6feb]/20 text-[#58a6ff] border border-[#58a6ff]/30' : 'bg-[#ddf4ff] text-[#0969da] border border-[#0969da]/30';
  return isDark.value ? 'bg-[#21262d] text-[#7d8590] border border-[#30363d]' : 'bg-[#f6f8fa] text-[#57606a] border border-[#d0d7de]';
};

const formatTime = (iso: string) => {
  if (!iso) return '--';
  return new Date(iso).toLocaleString('zh-CN', { hour12: false });
};

const statusIcon = (status: string) => {
  const s = status.toLowerCase();
  if (s === 'running') return Loader2;
  if (s === 'success') return CheckCircle2;
  if (s === 'error') return AlertCircle;
  return null;
};

// --- Template Helpers ---
const normalizeTemplate = (tpl: any) => {
  if (!tpl) return tpl;
  return {
    ...tpl,
    id: tpl.id ?? tpl.ID ?? tpl.Id,
    name: tpl.name ?? tpl.Name,
    task_type: tpl.task_type ?? tpl.TaskType ?? tpl.taskType,
    config: getTemplateConfig(tpl),
  };
};

const getTemplateConfig = (tpl: any) => {
  if (!tpl) return {};
  return tpl.config ?? tpl.ConfigJSON ?? tpl.config_json ?? tpl.Config ?? {};
};

const formatTemplateConfig = (tpl: any) => {
  const cfg = getTemplateConfig(tpl);
  try { return JSON.stringify(cfg, null, 2); } catch { return String(cfg); }
};

const templateByType = computed<Record<PipelineTaskType, any | undefined>>(() => {
  const base: Record<PipelineTaskType, any | undefined> = {
    collect_binance: undefined,
    collect_uniswap: undefined,
    process_prices: undefined,
    analyse: undefined,
  };
  templates.value.forEach((tpl) => {
    if (tpl.task_type && tpl.task_type in base) {
      base[tpl.task_type as PipelineTaskType] = tpl;
    }
  });
  return base;
});

// --- Date Parsers ---
const parseShanghaiDateTime = (value: string) => {
  if (!value) return undefined;
  const [datePart, timePart] = value.split('T');
  if (!datePart || !timePart) return undefined;
  const dParts = datePart.split('-').map(Number);
  const tParts = timePart.split(':').map(Number);
  const year = dParts[0] ?? 0;
  const month = dParts[1] ?? 0;
  const day = dParts[2] ?? 0;
  const hour = tParts[0] ?? 0;
  const minute = tParts[1] ?? 0;
  const second = tParts[2] ?? 0;
  if ([year, month, day, hour, minute, second].some(n => Number.isNaN(n))) return undefined;
  const date = new Date(Date.UTC(year, month - 1, day, hour - 8, minute, second));
  return Number.isNaN(date.getTime()) ? undefined : date;
};

const toUnixSeconds = (value: string) => {
  const parsed = parseShanghaiDateTime(value);
  if (!parsed) return undefined;
  return Math.floor(parsed.getTime() / 1000);
};

const toISODateTime = (value: string) => {
  const parsed = parseShanghaiDateTime(value);
  if (!parsed) return undefined;
  return parsed.toISOString();
};

const buildOverrides = (taskType: PipelineTaskType): Record<string, unknown> => {
  switch (taskType) {
    case 'collect_binance': return { ...templateConfigs.collect_binance };
    case 'collect_uniswap': {
      const { pool_address, start_date, end_date } = templateConfigs.collect_uniswap;
      const overrides: Record<string, unknown> = { pool_address };
      const startTs = toUnixSeconds(start_date);
      if (typeof startTs === 'number') overrides.start_ts = startTs;
      const endTs = toUnixSeconds(end_date);
      if (typeof endTs === 'number') overrides.end_ts = endTs;
      return overrides;
    }
    case 'process_prices': {
      const overrides: Record<string, unknown> = { ...templateConfigs.process_prices };
      const startISO = toISODateTime(templateConfigs.process_prices.start_date);
      if (startISO) overrides.start_date = startISO;
      const endISO = toISODateTime(templateConfigs.process_prices.end_date);
      if (endISO) overrides.end_date = endISO;
      return overrides;
    }
    case 'analyse': {
      const { batch_id, overwrite, strategy} = templateConfigs.analyse;
      const overrides: Record<string, unknown> = { overwrite, strategy: { ...strategy } };
      if (batch_id !== '') {
        const parsed = Number(batch_id);
        if (!Number.isNaN(parsed) && parsed > 0) overrides.batch_id = parsed;
      }
      const startISO = toISODateTime(strategy.start);
      if (startISO) overrides.strategy = { ...strategy, start: startISO };
      const endISO = toISODateTime(strategy.end);
      if (endISO) overrides.strategy = { ...strategy, end: endISO };
      return overrides;
    }
    default: return {};
  }
};

const updateTaskState = (taskType: PipelineTaskType, payload: Partial<Task>) => {
  tasks.value = tasks.value.map((task) => task.taskType === taskType ? { ...task, ...payload } : task);
};

// --- API Actions ---

// 修复：确保所有字段都有默认值，符合 Report 接口定义
const normalizeReport = (r: any): Report => {
  return {
    id: r.id ?? r.ID ?? 0,
    batch_id: r.batch_id ?? r.BatchID ?? 0,
    template_id: r.template_id ?? r.TemplateID ?? 0,
    format: r.format ?? r.Format ?? 'PDF',
    status: r.status ?? r.Status ?? 'PENDING',
    file_url: r.file_url ?? r.FileUrl ?? '',
    file_path: r.file_path ?? r.FilePath ?? '',
    created_at: r.created_at ?? r.CreatedAt ?? new Date().toISOString()
  };
};

const fetchAllData = async () => {
  await Promise.all([fetchControlData(), fetchBatches(), fetchReports()]);
};

const fetchControlData = async () => {
  isLoadingControl.value = true;
  try {
    const [taskRes, templateRes] = await Promise.all([
      api.getTasks({ page: 1, limit: 5 }),
      api.getTemplates(),
    ]);
    remoteTasks.value = taskRes.data?.data?.items ?? [];
    const rawTemplates = templateRes.data?.data ?? templateRes.data ?? [];
    templates.value = rawTemplates.map((t: any) => normalizeTemplate(t));
  } catch (e: any) {
    controlError.value = e.message;
  } finally {
    isLoadingControl.value = false;
  }
};

const fetchBatches = async () => {
  try {
    const res = await api.getBatches();
    batches.value = res.data?.data ?? res.data ?? [];
  } catch (e) { console.error(e); }
};

const fetchReports = async () => {
  isLoadingReports.value = true;
  try {
    const res = await api.getReports();
    const backendData = res.data?.data;
    let rawReports = [];
    if (Array.isArray(backendData)) {
      rawReports = backendData;
    } else if (backendData && Array.isArray(backendData.items)) {
      rawReports = backendData.items;
    }
    reports.value = rawReports.map(normalizeReport);
  } catch (e) {
    console.error("Failed to fetch reports", e);
  } finally {
    isLoadingReports.value = false;
  }
};

const handleCreateReport = async () => {
  if (!reportForm.batch_id) {
    alert('Please select a batch.');
    return;
  }
  isGeneratingReport.value = true;
  try {
    await api.createReport({
      batch_id: Number(reportForm.batch_id),
      template_id: reportForm.template_id ? Number(reportForm.template_id) : undefined,
      format: reportForm.format
    });
    showReportModal.value = false;
    await fetchReports();
  } catch (e: any) {
    alert('Failed to generate report: ' + e.message);
  } finally {
    isGeneratingReport.value = false;
  }
};

const handleDeleteReport = async (id: number) => {
  if (!confirm('Are you sure you want to delete this report?')) return;
  try {
    await api.deleteReport(id);
    reports.value = reports.value.filter(r => r.id !== id);
  } catch (e: any) {
    alert('Failed to delete report: ' + e.message);
  }
};

// --- Task Control Variables ---
const runningTemplateId = ref<number | null>(null);
const creatingTemplateType = ref<PipelineTaskType | null>(null);
const deletingTemplateId = ref<number | null>(null);

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

const createTemplateForTask = async (taskType: PipelineTaskType, silent = false) => {
  if (!silent) {
    creatingTemplateType.value = taskType;
    controlError.value = '';
  }
  try {
    const config = buildOverrides(taskType);
    const name = `Template ${new Date().toLocaleString('zh-CN', { hour12: false })}`;
    await api.createTemplate({ name, task_type: taskType, config });
    await fetchControlData();
    return templateByType.value[taskType];
  } catch (error: any) {
    if (!silent) controlError.value = error?.message ?? '创建模板失败';
    throw error;
  } finally {
    if (!silent) creatingTemplateType.value = null;
  }
};

const handleDeleteTemplate = async (id: number) => {
  if (!confirm('确定删除该模板？')) return;
  deletingTemplateId.value = id;
  try {
    await api.deleteTemplate(id);
    await fetchControlData();
  } catch (error: any) {
    controlError.value = error?.message ?? '删除模板失败';
  } finally {
    deletingTemplateId.value = null;
  }
};

const runPipelineTask = async (taskType: PipelineTaskType) => {
  controlError.value = '';
  let template = templateByType.value[taskType];
  if (!template) {
    try {
      template = await createTemplateForTask(taskType, true);
    } catch (error) {
      updateTaskState(taskType, { status: 'error' });
      return;
    }
  }
  updateTaskState(taskType, { status: 'running' });
  try {
    const overrides = buildOverrides(taskType);
    await api.runTemplate(template.id, { overrides });
    updateTaskState(taskType, { status: 'success', lastRun: new Date().toLocaleString('en-US') });
    await fetchControlData();
  } catch (error: any) {
    updateTaskState(taskType, { status: 'error' });
  }
};

const submitLegacyReport = async () => {
  if (!legacyReportForm.value.batch_id) return;
  try {
    await api.createReport({
      batch_id: Number(legacyReportForm.value.batch_id),
      template_id: legacyReportForm.value.template_id ? Number(legacyReportForm.value.template_id) : undefined,
      format: legacyReportForm.value.format,
    });
    await fetchReports();
  } catch (e) { console.error(e); }
};

onMounted(fetchAllData);
</script>

<template>
  <div class="space-y-6">
    
    <div class="rounded-md border p-4 space-y-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <FileText class="w-5 h-5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
          <h2 class="text-base font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Report Management</h2>
        </div>
        <button 
          @click="showReportModal = true"
          class="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md bg-[#238636] text-white hover:bg-[#2ea043] transition-colors"
        >
          <Plus class="w-4 h-4" /> New Report
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="text-xs border-b" :class="isDark ? 'text-[#7d8590] border-[#30363d]' : 'text-[#57606a] border-[#d0d7de]'">
              <th class="py-2 px-3">ID</th>
              <th class="py-2 px-3">Batch</th>
              <th class="py-2 px-3">Format</th>
              <th class="py-2 px-3">Created At</th>
              <th class="py-2 px-3">Status</th>
              <th class="py-2 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="text-sm">
            <tr v-if="isLoadingReports">
              <td colspan="6" class="py-4 text-center text-xs text-gray-500"><Loader2 class="w-4 h-4 animate-spin inline mr-2"/>Loading reports...</td>
            </tr>
            <tr v-else-if="reports.length === 0">
              <td colspan="6" class="py-4 text-center text-xs text-gray-500">No reports generated yet.</td>
            </tr>
            <tr 
              v-for="report in reports" 
              :key="report.id" 
              class="border-b last:border-0 transition-colors"
              :class="isDark ? 'border-[#30363d] hover:bg-[#0d1117]' : 'border-[#d0d7de] hover:bg-[#f6f8fa]'"
            >
              <td class="py-2 px-3 font-mono text-xs" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">#{{ report.id }}</td>
              <td class="py-2 px-3" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Batch #{{ report.batch_id }}</td>
              <td class="py-2 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] border font-medium uppercase">{{ report.format }}</span></td>
              <td class="py-2 px-3 text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">{{ formatTime(report.created_at) }}</td>
              <td class="py-2 px-3">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border" :class="statusAccent(report.status)">
                  <Loader2 v-if="report.status.toUpperCase() === 'GENERATING'" class="w-3 h-3 animate-spin mr-1"/>
                  {{ statusLabel(report.status) }}
                </span>
              </td>
              <td class="py-2 px-3 text-right flex items-center justify-end gap-2">
                <a 
                  v-if="(report.status.toUpperCase() === 'SUCCESS') && (report.file_url || report.file_path)" 
                  :href="`${backendURL}/reports/${report.id}/download`" 
                  target="_blank"
                  class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-blue-500 transition-colors"
                  title="Download"
                >
                  <FileDown class="w-4 h-4" />
                </a>
                <button 
                  @click="handleDeleteReport(report.id)"
                  class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-red-500 transition-colors"
                  title="Delete"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="rounded-md border p-4 space-y-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
      <div class="flex items-center gap-2">
        <Play class="w-4 h-4" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
        <h2 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Pipeline Control</h2>
      </div>
      <p v-if="controlError" class="text-xs text-[#f85149]">{{ controlError }}</p>
      <div class="space-y-3">
        <div v-for="task in tasks" :key="task.id" class="border rounded-md p-3 transition-colors" :class="isDark ? 'border-[#30363d] hover:border-[#58a6ff] bg-[#0d1117]' : 'border-[#d0d7de] hover:border-[#0969da] bg-[#f6f8fa]'">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div class="flex items-center gap-3 flex-1">
              <div class="w-10 h-10 rounded flex items-center justify-center" :class="{ 'bg-[#26a64126] text-[#3fb950]': task.status === 'success' && isDark, 'bg-[#ddf4ff] text-[#0969da]': task.status === 'running' && !isDark, 'bg-[#21262d] text-[#7d8590]': task.status === 'idle' && isDark, 'bg-[#eaeef2] text-[#57606a]': task.status === 'idle' && !isDark }">
                <component v-if="iconMap[task.icon]" :is="iconMap[task.icon]" class="w-4 h-4" />
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="text-sm" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ task.name }}</h3>
                  <component v-if="statusIcon(task.status)" :is="statusIcon(task.status)" class="w-4 h-4" :class="statusAccent(task.status)" />
                </div>
                <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">{{ task.description }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button v-if="!templateByType[task.taskType]" class="px-2 py-1 text-xs rounded border transition-colors" :class="isDark ? 'border-[#30363d] text-[#7d8590]' : 'border-[#d0d7de] text-[#57606a]'" @click="createTemplateForTask(task.taskType)">{{ creatingTemplateType === task.taskType ? '创建中…' : '创建模板' }}</button>
              <button class="px-3 py-1.5 bg-[#238636] text-white rounded text-sm hover:bg-[#2ea043]" :disabled="task.status === 'running'" @click="runPipelineTask(task.taskType)">Run</button>
            </div>
          </div>
          
          <div class="mt-3 pt-3 border-t" :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'">
             <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <template v-if="task.taskType === 'collect_binance'">
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>CSV Path</span><input v-model="templateConfigs.collect_binance.csv_path" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Import %</span><input type="number" v-model.number="templateConfigs.collect_binance.import_percentage" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Chunk Size</span><input type="number" v-model.number="templateConfigs.collect_binance.chunk_size" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                </template>
                <template v-else-if="task.taskType === 'collect_uniswap'">
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Pool Address</span><input v-model="templateConfigs.collect_uniswap.pool_address" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Start DateTime</span><input type="datetime-local" step="1" v-model="templateConfigs.collect_uniswap.start_date" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>End DateTime</span><input type="datetime-local" step="1" v-model="templateConfigs.collect_uniswap.end_date" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                </template>
                <template v-else-if="task.taskType === 'process_prices'">
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Start DateTime</span><input type="datetime-local" step="1" v-model="templateConfigs.process_prices.start_date" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>End DateTime</span><input type="datetime-local" step="1" v-model="templateConfigs.process_prices.end_date" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Interval</span><select v-model="templateConfigs.process_prices.aggregation_interval" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]"><option value="1m">1m</option><option value="5m">5m</option><option value="15m">15m</option><option value="1h">1h</option></select></label>
                  <label :class="[labelTextClass, 'flex items-center gap-2']"><input type="checkbox" v-model="templateConfigs.process_prices.overwrite" />覆盖旧数据</label>
                </template>
                <template v-else>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']"><span>Batch ID（可选）</span><input type="text" inputmode="numeric" placeholder="留空自动创建批次" v-model="templateConfigs.analyse.batch_id" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" /></label>
                  <label :class="[labelTextClass, 'flex items-center gap-2']"><input type="checkbox" v-model="templateConfigs.analyse.overwrite" />覆盖批次</label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']">
                    <span>分析开始时间</span>
                    <input type="datetime-local" step="1" v-model="templateConfigs.analyse.strategy.start" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                  </label>
                  <label :class="[labelTextClass, 'flex flex-col gap-1']">
                    <span>分析结束时间</span>
                    <input type="datetime-local" step="1" v-model="templateConfigs.analyse.strategy.end" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                  </label>
                  <div class="col-span-1 md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-3 border-t pt-2 mt-2" :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'">
                    <label :class="[labelTextClass, 'flex flex-col gap-1']">
                      <span>Profit Threshold (USDT)</span>
                      <input type="number" v-model.number="templateConfigs.analyse.strategy.profit_threshold" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                    </label>
                    <label :class="[labelTextClass, 'flex flex-col gap-1']">
                      <span>Time Delay (s)</span>
                      <input type="number" v-model.number="templateConfigs.analyse.strategy.time_delay_seconds" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                    </label>
                    <label :class="[labelTextClass, 'flex flex-col gap-1']">
                      <span>Initial Investment (USDT)</span>
                      <input type="number" v-model.number="templateConfigs.analyse.strategy.initial_investment" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                    </label>
                  </div>
                </template>
             </div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="rounded-md border p-4 space-y-3" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between">
          <h3 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Template Actions</h3>
          <button class="text-xs" :class="isDark ? 'text-[#58a6ff]' : 'text-[#0969da]'" @click="fetchControlData">Reload</button>
        </div>
        <div v-if="templates.length === 0" class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">暂无模板。</div>
        <div v-for="template in templates.slice(0, 3)" :key="template.id" class="border rounded px-3 py-2 space-y-1" :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ template.name }}</div>
            <div class="flex gap-2">
              <button class="text-xs text-red-500 hover:underline" @click="handleDeleteTemplate(template.id)">Delete</button>
              <button class="text-xs text-green-500 hover:underline" @click="runTemplateQuick(template.id)">Run</button>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-md border p-4 space-y-3" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between">
          <h3 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Legacy Quick Report</h3>
        </div>
        <div class="grid grid-cols-1 gap-2 text-xs">
          <input v-model="legacyReportForm.batch_id" type="number" placeholder="Batch ID" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
          <button class="w-full px-3 py-1.5 bg-[#238636] text-white text-xs rounded" @click="submitLegacyReport">Submit</button>
        </div>
      </div>
    </div>

    <div v-if="showReportModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="w-full max-w-md rounded-lg shadow-xl overflow-hidden animate-in zoom-in duration-200" :class="isDark ? 'bg-[#161b22] border border-[#30363d]' : 'bg-white'">
        <div class="px-4 py-3 border-b flex justify-between items-center" :class="isDark ? 'border-[#30363d]' : 'border-gray-200'">
          <h3 class="font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Generate New Report</h3>
          <button @click="showReportModal = false"><X class="w-5 h-5 text-gray-500" /></button>
        </div>
        <div class="p-4 space-y-4">
          <div>
            <label class="block text-xs mb-1" :class="labelTextClass">Select Batch <span class="text-red-500">*</span></label>
            <select v-model="reportForm.batch_id" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]">
              <option value="" disabled>-- Choose a Batch --</option>
              <option v-for="b in batches" :key="b.id" :value="b.id">{{ b.name }} (ID: {{ b.id }})</option>
            </select>
          </div>
          <div>
            <label class="block text-xs mb-1" :class="labelTextClass">Report Template</label>
            <select v-model="reportForm.template_id" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]">
              <option value="">Default Template</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs mb-1" :class="labelTextClass">Output Format</label>
            <div class="flex gap-2">
              <button 
                v-for="fmt in ['PDF', 'HTML', 'Markdown']" :key="fmt"
                type="button"
                class="flex-1 py-1.5 text-xs rounded border transition-colors"
                :class="reportForm.format === fmt ? 'bg-blue-600 text-white border-blue-600' : (isDark ? 'border-gray-700 hover:border-gray-500 text-gray-300' : 'border-gray-300 hover:border-gray-400 text-gray-700')"
                @click="reportForm.format = fmt as ReportFormat"
              >
                {{ fmt }}
              </button>
            </div>
          </div>
        </div>
        <div class="px-4 py-3 border-t bg-opacity-50 flex justify-end gap-2" :class="isDark ? 'bg-[#0d1117] border-[#30363d]' : 'bg-gray-50 border-gray-200'">
          <button @click="showReportModal = false" class="px-3 py-1.5 rounded text-xs border text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">Cancel</button>
          <button 
            @click="handleCreateReport" 
            :disabled="isGeneratingReport || !reportForm.batch_id"
            class="px-3 py-1.5 rounded text-xs bg-[#238636] text-white hover:bg-[#2ea043] disabled:opacity-50 flex items-center gap-1"
          >
            <Loader2 v-if="isGeneratingReport" class="w-3 h-3 animate-spin" />
            {{ isGeneratingReport ? 'Generating...' : 'Generate' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>