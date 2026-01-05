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
  config?: Record<string, unknown>;
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

const reportActionMessage = ref('');
const reportActionError = ref('');
const legacyReportLoading = ref(false);

const templateConfigs = reactive<TemplateConfigs>({
  collect_binance: { csv_path: '/data/binance_aggTrades_ETHUSDT.csv', import_percentage: 100, chunk_size: 1000000 },
  collect_uniswap: { pool_address: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640', start_date: '', end_date: '' },
  process_prices: { start_date: '', end_date: '', aggregation_interval: '5m', overwrite: true },
  analyse: { batch_id: '', overwrite: false, strategy: { profit_threshold: 0.5, time_delay_seconds: 15, initial_investment: 10000, start: '', end: '' } },
});

const tasks = ref<Task[]>([
  { id: 'collect-binance', taskType: 'collect_binance', name: '导入 Binance 数据', description: '从 CSV 导入币安历史成交数据', icon: 'download', status: 'idle' },
  { id: 'collect-uniswap', taskType: 'collect_uniswap', name: '抓取 Uniswap 数据', description: '从 The Graph 拉取链上交易数据', icon: 'download', status: 'idle' },
  { id: 'process-prices', taskType: 'process_prices', name: '价格聚合', description: '将原始数据聚合为可查询的价格序列', icon: 'database', status: 'idle' },
  { id: 'analyse', taskType: 'analyse', name: '套利分析', description: '在历史窗口中识别潜在套利机会', icon: 'trending', status: 'idle' },
]);

const latestRangeOptions = [
  { label: '最近 1 小时', seconds: 60 * 60 },
  { label: '最近 6 小时', seconds: 6 * 60 * 60 },
  { label: '最近 24 小时', seconds: 24 * 60 * 60 },
  { label: '最近 7 天', seconds: 7 * 24 * 60 * 60 },
] as const;

const latestRangeSeconds = ref<number>(latestRangeOptions[1].seconds);
const latestDownloadLoading = ref(false);

const labelTextClass = computed(() => (isDark.value ? 'text-[#e6edf3]' : 'text-[#24292f]'));
const baseInputClass = 'w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-xs focus:border-transparent transition-all';
const darkInputClass = 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]';
const lightInputClass = 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]';

const iconMap: Record<TaskIcon, any> = { download: Download, database: Database, trending: TrendingUp };

const statusLabel = (status: string) => {
  if (!status) return '未知';
  switch (status.toUpperCase()) {
    case 'RUNNING': case 'GENERATING': return '运行中';
    case 'SUCCESS': return '成功';
    case 'ERROR': case 'FAILED': return '失败';
    case 'PENDING': return '等待中';
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

/*
const formatTemplateConfig = (tpl: any) => {
  const cfg = getTemplateConfig(tpl);
  try { return JSON.stringify(cfg, null, 2); } catch { return String(cfg); }
};
*/

const templateByType = computed<Record<PipelineTaskType, any | undefined>>(() => {
  const base: Record<PipelineTaskType, any | undefined> = {
    collect_binance: undefined,
    collect_uniswap: undefined,
    process_prices: undefined,
    analyse: undefined,
  };
  templates.value.forEach((tpl) => {
    if (tpl.task_type && tpl.task_type in base) {
      const key = tpl.task_type as PipelineTaskType;
      if (!base[key]) base[key] = tpl;
    }
  });
  return base;
});

const hasSyncedTemplateConfigs = ref(false);

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

const toFiniteNumber = (value: unknown): number | undefined => {
  if (value == null) return undefined;
  if (typeof value === 'number') return Number.isFinite(value) ? value : undefined;
  const n = Number(String(value));
  return Number.isFinite(n) ? n : undefined;
};

const toOptionalBoolean = (value: unknown): boolean | undefined => {
  if (value == null) return undefined;
  if (typeof value === 'boolean') return value;
  const s = String(value).trim().toLowerCase();
  if (s === 'true') return true;
  if (s === 'false') return false;
  return undefined;
};

const toShanghaiInputValue = (value: unknown): string => {
  if (value == null) return '';
  let date: Date | null = null;
  const asNumber = toFiniteNumber(value);
  if (asNumber != null) {
    date = new Date(asNumber * 1000);
  } else if (typeof value === 'string') {
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) date = d;
  }
  if (!date || Number.isNaN(date.getTime())) return '';
  const shanghai = new Date(date.getTime() + 8 * 60 * 60 * 1000);
  return shanghai.toISOString().slice(0, 19);
};

const syncTemplateConfigsFromTemplates = () => {
  const byType = templateByType.value;

  const binance = byType.collect_binance?.config ?? {};
  if (typeof binance.csv_path === 'string') templateConfigs.collect_binance.csv_path = binance.csv_path;
  const importPct = toFiniteNumber(binance.import_percentage);
  if (importPct != null) templateConfigs.collect_binance.import_percentage = importPct;
  const chunkSize = toFiniteNumber(binance.chunk_size);
  if (chunkSize != null) templateConfigs.collect_binance.chunk_size = chunkSize;

  const uniswap = byType.collect_uniswap?.config ?? {};
  if (typeof uniswap.pool_address === 'string') templateConfigs.collect_uniswap.pool_address = uniswap.pool_address;
  const uStart = toShanghaiInputValue(uniswap.start_ts ?? uniswap.start_date ?? uniswap.start);
  const uEnd = toShanghaiInputValue(uniswap.end_ts ?? uniswap.end_date ?? uniswap.end);
  if (uStart) templateConfigs.collect_uniswap.start_date = uStart;
  if (uEnd) templateConfigs.collect_uniswap.end_date = uEnd;

  const prices = byType.process_prices?.config ?? {};
  const pStart = toShanghaiInputValue(prices.start_date ?? prices.start);
  const pEnd = toShanghaiInputValue(prices.end_date ?? prices.end);
  if (pStart) templateConfigs.process_prices.start_date = pStart;
  if (pEnd) templateConfigs.process_prices.end_date = pEnd;
  if (typeof prices.aggregation_interval === 'string') templateConfigs.process_prices.aggregation_interval = prices.aggregation_interval;
  const overwrite = toOptionalBoolean(prices.overwrite);
  if (overwrite != null) templateConfigs.process_prices.overwrite = overwrite;

  const analyse = byType.analyse?.config ?? {};
  const batchId = analyse.batch_id != null ? String(analyse.batch_id) : '';
  if (batchId) templateConfigs.analyse.batch_id = batchId;
  const aOverwrite = toOptionalBoolean(analyse.overwrite);
  if (aOverwrite != null) templateConfigs.analyse.overwrite = aOverwrite;
  const strategy = (analyse.strategy ?? {}) as Record<string, unknown>;
  const profit = toFiniteNumber(strategy.profit_threshold);
  if (profit != null) templateConfigs.analyse.strategy.profit_threshold = profit;
  const delay = toFiniteNumber(strategy.time_delay_seconds);
  if (delay != null) templateConfigs.analyse.strategy.time_delay_seconds = delay;
  const invest = toFiniteNumber(strategy.initial_investment);
  if (invest != null) templateConfigs.analyse.strategy.initial_investment = invest;
  const aStart = toShanghaiInputValue(strategy.start);
  const aEnd = toShanghaiInputValue(strategy.end);
  if (aStart) templateConfigs.analyse.strategy.start = aStart;
  if (aEnd) templateConfigs.analyse.strategy.end = aEnd;
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

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const toAbsoluteDownloadUrl = (reportId: number) => `${backendURL}/reports/${reportId}/download`;

const downloadReport = (reportId: number) => {
  const url = toAbsoluteDownloadUrl(reportId);
  const win = window.open(url, '_blank', 'noopener,noreferrer');
  if (!win) {
    window.location.href = url;
  }
};

const pickLatestTemplateByType = (taskType: string): Template | undefined => {
  let best: Template | undefined;
  for (const tpl of templates.value) {
    if (tpl.task_type !== taskType) continue;
    if (!best || tpl.id > best.id) best = tpl;
  }
  return best;
};

const ensureTemplateByType = async (taskType: string): Promise<Template> => {
  const existing = pickLatestTemplateByType(taskType);
  if (existing) return existing;

  const name = `Auto ${taskType} ${new Date().toLocaleString('zh-CN', { hour12: false })}`;
  await api.createTemplate({ name, task_type: taskType, config: {} });
  await fetchControlData();
  const created = pickLatestTemplateByType(taskType);
  if (!created) throw new Error(`模板创建失败: ${taskType}`);
  return created;
};

const downloadLatestData = async () => {
  controlError.value = '';
  latestDownloadLoading.value = true;
  try {
    const endTs = Math.floor(Date.now() / 1000);
    const startTs = Math.max(0, endTs - latestRangeSeconds.value);

    const binanceTpl = await ensureTemplateByType('collect_binance_by_date');
    await api.runTemplate(binanceTpl.id, { overrides: { start_ts: startTs, end_ts: endTs } });

    const uniswapTpl = await ensureTemplateByType('collect_uniswap');
    await api.runTemplate(uniswapTpl.id, {
      overrides: {
        pool_address: templateConfigs.collect_uniswap.pool_address,
        start_ts: startTs,
        end_ts: endTs,
      },
    });

    await fetchControlData();
  } catch (error: any) {
    controlError.value = error?.message ?? '下载最新数据失败';
  } finally {
    latestDownloadLoading.value = false;
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

const fetchControlData = async (forceSync = false) => {
  isLoadingControl.value = true;
  try {
    const [taskRes, templateRes] = await Promise.all([
      api.getTasks({ page: 1, limit: 5 }),
      api.getTemplates(),
    ]);
    remoteTasks.value = taskRes.data?.data?.items ?? [];
    const rawTemplates = templateRes.data?.data ?? templateRes.data ?? [];
    templates.value = rawTemplates.map((t: any) => normalizeTemplate(t));
    if (forceSync || !hasSyncedTemplateConfigs.value) {
      syncTemplateConfigsFromTemplates();
      hasSyncedTemplateConfigs.value = true;
    }
  } catch (e: any) {
    controlError.value = e.message;
  } finally {
    isLoadingControl.value = false;
  }
};

const reloadControlData = async () => {
  await fetchControlData(true);
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
    alert('请先选择批次');
    return;
  }
  isGeneratingReport.value = true;
  reportActionMessage.value = '';
  reportActionError.value = '';
  try {
    const { data } = await api.createReport({
      batch_id: Number(reportForm.batch_id),
      template_id: reportForm.template_id ? Number(reportForm.template_id) : undefined,
      format: reportForm.format
    });
    showReportModal.value = false;
    const reportId = data?.data?.id ?? data?.id;
    reportActionMessage.value = reportId ? `已提交报告生成请求：Report #${reportId}` : '已提交报告生成请求';
    await fetchReports();

    if (reportId) {
      for (let i = 0; i < 12; i += 1) {
        await sleep(1200);
        await fetchReports();
        const found = reports.value.find((r) => r.id === reportId);
        const st = String(found?.status ?? '').toUpperCase();
        if (st === 'SUCCESS' || st === 'FAILED') break;
      }
    }
  } catch (e: any) {
    reportActionError.value = e?.message ?? '生成报告失败';
  } finally {
    isGeneratingReport.value = false;
  }
};

const handleDeleteReport = async (id: number) => {
  if (!confirm('确定删除该报告吗？')) return;
  try {
    await api.deleteReport(id);
    reports.value = reports.value.filter(r => r.id !== id);
  } catch (e: any) {
    alert('删除报告失败：' + e.message);
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
    updateTaskState(taskType, { status: 'success', lastRun: new Date().toLocaleString('zh-CN', { hour12: false }) });
    await fetchControlData();
  } catch (error: any) {
    updateTaskState(taskType, { status: 'error' });
  }
};

const submitLegacyReport = async () => {
  if (!legacyReportForm.value.batch_id) return;
  legacyReportLoading.value = true;
  reportActionMessage.value = '';
  reportActionError.value = '';
  try {
    const { data } = await api.createReport({
      batch_id: Number(legacyReportForm.value.batch_id),
      template_id: legacyReportForm.value.template_id ? Number(legacyReportForm.value.template_id) : undefined,
      format: legacyReportForm.value.format,
    });
    await fetchReports();
    const reportId = data?.data?.id ?? data?.id;
    reportActionMessage.value = reportId ? `已提交报告生成请求：Report #${reportId}` : '已提交报告生成请求';

    if (reportId) {
      for (let i = 0; i < 12; i += 1) {
        await sleep(1200);
        await fetchReports();
        const found = reports.value.find((r) => r.id === reportId);
        const st = String(found?.status ?? '').toUpperCase();
        if (st === 'SUCCESS' || st === 'FAILED') break;
      }
    }
  } catch (e: any) {
    reportActionError.value = e?.message ?? '生成报告失败';
  } finally {
    legacyReportLoading.value = false;
  }
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
      <p v-if="reportActionError" class="text-xs text-[#f85149]">{{ reportActionError }}</p>
      <p v-else-if="reportActionMessage" class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">{{ reportActionMessage }}</p>

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
              <td class="py-2 px-3" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">批次 #{{ report.batch_id }}</td>
              <td class="py-2 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] border font-medium uppercase">{{ report.format }}</span></td>
              <td class="py-2 px-3 text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">{{ formatTime(report.created_at) }}</td>
              <td class="py-2 px-3">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border" :class="statusAccent(report.status)">
                  <Loader2 v-if="report.status.toUpperCase() === 'GENERATING'" class="w-3 h-3 animate-spin mr-1"/>
                  {{ statusLabel(report.status) }}
                </span>
              </td>
              <td class="py-2 px-3 text-right flex items-center justify-end gap-2">
                <button
                  v-if="(report.status.toUpperCase() === 'SUCCESS') && (report.file_url || report.file_path)" 
                  type="button"
                  @click="downloadReport(report.id)"
                  class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-blue-500 transition-colors"
                  title="下载"
                >
                  <FileDown class="w-4 h-4" />
                </button>
                <button 
                  @click="handleDeleteReport(report.id)"
                  class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-red-500 transition-colors"
                  title="删除"
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
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Play class="w-4 h-4" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'" />
          <h2 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">任务流水线</h2>
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model.number="latestRangeSeconds"
            class="px-2 py-1.5 text-xs rounded border"
            :class="isDark ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3]' : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f]'"
            :disabled="latestDownloadLoading"
          >
            <option v-for="opt in latestRangeOptions" :key="opt.seconds" :value="opt.seconds">{{ opt.label }}</option>
          </select>
          <button
            class="px-3 py-1.5 text-xs rounded bg-[#0969da] text-white hover:bg-[#1f6feb] disabled:opacity-60"
            :disabled="latestDownloadLoading"
            @click="downloadLatestData"
          >
            {{ latestDownloadLoading ? '下载中…' : '下载最新数据' }}
          </button>
        </div>
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
              <button class="px-3 py-1.5 bg-[#238636] text-white rounded text-sm hover:bg-[#2ea043]" :disabled="task.status === 'running'" @click="runPipelineTask(task.taskType)">运行</button>
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
                  <label :class="[labelTextClass, 'flex items-center gap-2']"><input type="checkbox" v-model="templateConfigs.analyse.overwrite" />覆盖当前批次（仅 batch_id）</label>
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
                      <span>利润阈值（USDT）</span>
                      <input type="number" v-model.number="templateConfigs.analyse.strategy.profit_threshold" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                    </label>
                    <label :class="[labelTextClass, 'flex flex-col gap-1']">
                      <span>延迟（秒）</span>
                      <input type="number" v-model.number="templateConfigs.analyse.strategy.time_delay_seconds" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
                    </label>
                    <label :class="[labelTextClass, 'flex flex-col gap-1']">
                      <span>初始资金（USDT）</span>
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
          <h3 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">模板操作</h3>
          <button class="text-xs" :class="isDark ? 'text-[#58a6ff]' : 'text-[#0969da]'" @click="reloadControlData">刷新</button>
        </div>
        <div v-if="templates.length === 0" class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">暂无模板。</div>
        <div v-for="template in templates.slice(0, 3)" :key="template.id" class="border rounded px-3 py-2 space-y-1" :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ template.name }}</div>
            <div class="flex gap-2">
              <button class="text-xs text-red-500 hover:underline" @click="handleDeleteTemplate(template.id)">删除</button>
              <button class="text-xs text-green-500 hover:underline" @click="runTemplateQuick(template.id)">运行</button>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-md border p-4 space-y-3" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between">
          <h3 :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">快速生成报告（兼容入口）</h3>
        </div>
        <div class="grid grid-cols-1 gap-2 text-xs">
          <input v-model="legacyReportForm.batch_id" type="number" placeholder="批次 ID" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]" />
          <button class="w-full px-3 py-1.5 bg-[#238636] text-white text-xs rounded disabled:opacity-60" :disabled="legacyReportLoading" @click="submitLegacyReport">
            {{ legacyReportLoading ? '提交中…' : '提交' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showReportModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div class="w-full max-w-md rounded-lg shadow-xl overflow-hidden animate-in zoom-in duration-200" :class="isDark ? 'bg-[#161b22] border border-[#30363d]' : 'bg-white'">
        <div class="px-4 py-3 border-b flex justify-between items-center" :class="isDark ? 'border-[#30363d]' : 'border-gray-200'">
          <h3 class="font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">生成新报告</h3>
          <button @click="showReportModal = false"><X class="w-5 h-5 text-gray-500" /></button>
        </div>
        <div class="p-4 space-y-4">
          <div>
            <label class="block text-xs mb-1" :class="labelTextClass">选择批次 <span class="text-red-500">*</span></label>
            <select v-model="reportForm.batch_id" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]">
              <option value="" disabled>-- 请选择批次 --</option>
              <option v-for="b in batches" :key="b.id" :value="b.id">{{ b.name }}（ID：{{ b.id }}）</option>
            </select>
          </div>
          <div>
            <label class="block text-xs mb-1" :class="labelTextClass">报告模板</label>
            <select v-model="reportForm.template_id" :class="[baseInputClass, isDark ? darkInputClass : lightInputClass]">
              <option value="">默认模板</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs mb-1" :class="labelTextClass">输出格式</label>
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
          <button @click="showReportModal = false" class="px-3 py-1.5 rounded text-xs border text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">取消</button>
          <button 
            @click="handleCreateReport" 
            :disabled="isGeneratingReport || !reportForm.batch_id"
            class="px-3 py-1.5 rounded text-xs bg-[#238636] text-white hover:bg-[#2ea043] disabled:opacity-50 flex items-center gap-1"
          >
            <Loader2 v-if="isGeneratingReport" class="w-3 h-3 animate-spin" />
            {{ isGeneratingReport ? '生成中…' : '生成' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
