<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import * as echarts from 'echarts';
import api, { type TemplatePayload } from '../api';
import { useRouter } from 'vue-router';

interface TemplateItem {
  id: number;
  name: string;
  task_type: string;
  config: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

type PipelineTaskType = 'collect_binance' | 'collect_uniswap' | 'process_prices' | 'analyse';

const router = useRouter();

const templates = ref<TemplateItem[]>([]);
const loading = ref(false);
const formVisible = ref(false);
const editId = ref<number | null>(null);
const runMessage = ref('');
const form = reactive<TemplatePayload>({
  name: '',
  task_type: 'collect_binance',
  config: {},
});
const errorMessage = ref('');
const quickMessage = ref('');
const quickLastTaskId = ref<string>('');
const quickLoading = reactive<Record<PipelineTaskType, boolean>>({
  collect_binance: false,
  collect_uniswap: false,
  process_prices: false,
  analyse: false,
});

const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const totalTemplates = computed(() => templates.value.length);
const typeCounts = computed(() => {
  const counts: Record<string, number> = {};
  for (const t of templates.value) {
    const key = t.task_type ?? 'unknown';
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
});

const getTemplateConfig = (tpl: any): Record<string, unknown> => {
  if (!tpl) return {};
  return tpl.config ?? tpl.ConfigJSON ?? tpl.config_json ?? tpl.Config ?? {};
};

const normalizeTemplate = (tpl: any): TemplateItem => {
  const normalized: any = {
    ...tpl,
    id: tpl?.id ?? tpl?.ID ?? tpl?.Id ?? 0,
    name: tpl?.name ?? tpl?.Name ?? '',
    task_type: tpl?.task_type ?? tpl?.TaskType ?? tpl?.taskType ?? '',
    config: getTemplateConfig(tpl),
    created_at: tpl?.created_at ?? tpl?.CreatedAt,
    updated_at: tpl?.updated_at ?? tpl?.UpdatedAt,
  };
  return normalized as TemplateItem;
};

const templatesByType = computed<Record<PipelineTaskType, TemplateItem[]>>(() => {
  const base: Record<PipelineTaskType, TemplateItem[]> = {
    collect_binance: [],
    collect_uniswap: [],
    process_prices: [],
    analyse: [],
  };
  for (const t of templates.value) {
    if (t.task_type in base) {
      base[t.task_type as PipelineTaskType].push(t);
    }
  }
  return base;
});

const templateOptionsByType = computed(() => ({
  collect_binance: templatesByType.value.collect_binance.map((t) => ({ label: `#${t.id} · ${t.name}`, value: t.id })),
  collect_uniswap: templatesByType.value.collect_uniswap.map((t) => ({ label: `#${t.id} · ${t.name}`, value: t.id })),
  process_prices: templatesByType.value.process_prices.map((t) => ({ label: `#${t.id} · ${t.name}`, value: t.id })),
  analyse: templatesByType.value.analyse.map((t) => ({ label: `#${t.id} · ${t.name}`, value: t.id })),
}));

const resetForm = () => {
  form.name = '';
  form.task_type = 'collect_binance';
  form.config = {};
  editId.value = null;
};

const fetchTemplates = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getTemplates();
    const raw = data?.data ?? data ?? [];
    templates.value = Array.isArray(raw) ? raw.map(normalizeTemplate) : [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '模板列表获取失败';
  } finally {
    loading.value = false;
    nextTick(renderChart);
  }
};

const openCreate = () => {
  resetForm();
  formVisible.value = true;
};

const submitForm = async () => {
  try {
    if (!form.name) {
      errorMessage.value = '请填写模板名称';
      return;
    }
    if (editId.value) {
      await api.updateTemplate(editId.value, form);
    } else {
      await api.createTemplate(form);
    }
    formVisible.value = false;
    runMessage.value = '';
    await fetchTemplates();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '模板保存失败';
  }
};

const editTemplate = (template: TemplateItem) => {
  editId.value = template.id;
  form.name = template.name;
  form.task_type = template.task_type;
  form.config = { ...template.config };
  formVisible.value = true;
};

const deleteTemplate = async (id: number) => {
  if (!confirm('确定删除该模板？')) return;
  try {
    await api.deleteTemplate(id);
    await fetchTemplates();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '删除失败';
  }
};

const runTemplate = async (id: number) => {
  try {
    runMessage.value = '正在运行模板...';
    const { data } = await api.runTemplate(id);
    const taskId = data?.data?.task_id ?? data?.task_id;
    runMessage.value = `模板已触发任务：${taskId}`;
  } catch (error: any) {
    runMessage.value = error?.message ?? '运行模板失败';
  }
};

const toUnixSeconds = (value: string): number | null => {
  if (!value) return null;
  const d = new Date(value);
  const t = d.getTime();
  if (!Number.isFinite(t)) return null;
  return Math.floor(t / 1000);
};

const toISOZ = (value: string): string | null => {
  if (!value) return null;
  const d = new Date(value);
  const t = d.getTime();
  if (!Number.isFinite(t)) return null;
  return d.toISOString();
};

const quickSelectedTemplateId = reactive<Record<PipelineTaskType, number | null>>({
  collect_binance: null,
  collect_uniswap: null,
  process_prices: null,
  analyse: null,
});

const quickParams = reactive({
  collect_binance: {
    csv_path: '/data/binance_aggTrades_ETHUSDT.csv',
    import_percentage: 100,
    chunk_size: 1000000,
  },
  collect_uniswap: {
    pool_address: '',
    start_time: '',
    end_time: '',
  },
  process_prices: {
    start_time: '',
    end_time: '',
    aggregation_interval: '5m',
    overwrite: true,
  },
  analyse: {
    batch_id: 1,
    overwrite: false,
    profit_threshold: 0.5,
    time_delay_seconds: 15,
    initial_investment: 10000,
    start_time: '',
    end_time: '',
  },
});

const pickTemplateId = (taskType: PipelineTaskType): number | null => {
  const selected = quickSelectedTemplateId[taskType];
  if (selected) return selected;
  const list = templatesByType.value[taskType];
  return list.length ? list[0]!.id : null;
};

const goTasks = () => router.push('/app/tasks');

const runQuick = async (taskType: PipelineTaskType) => {
  quickMessage.value = '';
  quickLastTaskId.value = '';

  const templateId = pickTemplateId(taskType);
  if (!templateId) {
    quickMessage.value = `未找到 ${taskType} 的模板，请先新建一个对应 task_type 的模板。`;
    return;
  }

  quickLoading[taskType] = true;
  try {
    let overrides: Record<string, unknown> = {};

    if (taskType === 'collect_binance') {
      overrides = {
        csv_path: quickParams.collect_binance.csv_path,
        import_percentage: quickParams.collect_binance.import_percentage,
        chunk_size: quickParams.collect_binance.chunk_size,
      };
    } else if (taskType === 'collect_uniswap') {
      const startTs = toUnixSeconds(quickParams.collect_uniswap.start_time);
      const endTs = toUnixSeconds(quickParams.collect_uniswap.end_time);
      overrides = {
        pool_address: quickParams.collect_uniswap.pool_address,
        start_ts: startTs ?? 0,
        end_ts: endTs ?? 0,
      };
    } else if (taskType === 'process_prices') {
      const startISO = toISOZ(quickParams.process_prices.start_time);
      const endISO = toISOZ(quickParams.process_prices.end_time);
      overrides = {
        start_date: startISO ?? undefined,
        end_date: endISO ?? undefined,
        aggregation_interval: quickParams.process_prices.aggregation_interval,
        overwrite: quickParams.process_prices.overwrite,
      };
    } else if (taskType === 'analyse') {
      const startISO = toISOZ(quickParams.analyse.start_time);
      const endISO = toISOZ(quickParams.analyse.end_time);
      const strategy: Record<string, unknown> = {
        profit_threshold: quickParams.analyse.profit_threshold,
        time_delay_seconds: quickParams.analyse.time_delay_seconds,
        initial_investment: quickParams.analyse.initial_investment,
      };
      if (startISO) strategy.start = startISO;
      if (endISO) strategy.end = endISO;
      overrides = {
        batch_id: quickParams.analyse.batch_id,
        overwrite: quickParams.analyse.overwrite,
        strategy,
      };
    }

    const { data } = await api.runTemplate(templateId, { overrides, trigger: 'quick_run' });
    const taskId = data?.data?.task_id ?? data?.task_id;
    quickLastTaskId.value = String(taskId ?? '');
    quickMessage.value = taskId ? `已触发任务：${taskId}` : '已触发任务';
  } catch (error: any) {
    quickMessage.value = error?.message ?? '运行失败';
  } finally {
    quickLoading[taskType] = false;
  }
};

const formattedConfig = computed(() => JSON.stringify(form.config, null, 2));

const handleConfigChange = (event: Event) => {
  const value = (event.target as HTMLTextAreaElement).value;
  try {
    form.config = value ? JSON.parse(value) : {};
    errorMessage.value = '';
  } catch (error) {
    errorMessage.value = '配置必须为合法 JSON';
  }
};

onMounted(fetchTemplates);

const renderChart = () => {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);
  const entries = Object.entries(typeCounts.value)
    .map(([name, value]) => ({ name, value }))
    .filter((x) => x.value > 0);
  chart.setOption({
    tooltip: { trigger: 'item' },
    toolbox: { feature: { saveAsImage: {} } },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '45%'],
        data: entries,
        label: { formatter: '{b}: {c}' },
      },
    ],
  });
};

watch(
  () => templates.value,
  () => nextTick(renderChart),
  { deep: true },
);

onBeforeUnmount(() => {
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div class="p-6 lg:p-8 space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-[#24292f] dark:text-[#e6edf3]">模板管理</h1>
        <p class="text-sm text-[#57606a] dark:text-[#7d8590]">维护任务参数模板，支持一键运行。</p>
      </div>
      <button
        type="button"
        class="px-4 py-2 rounded bg-blue-600 text-white text-sm"
        @click="openCreate"
      >
        新建模板
      </button>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>
    <div v-if="runMessage" class="bg-blue-50 text-blue-700 text-sm rounded p-3">
      {{ runMessage }}
    </div>
    <div v-if="quickMessage" class="bg-blue-50 text-blue-700 text-sm rounded p-3 flex items-center justify-between gap-3">
      <div>{{ quickMessage }}</div>
      <div v-if="quickLastTaskId" class="flex items-center gap-3">
        <span class="text-xs text-[#57606a] dark:text-[#7d8590] font-mono">{{ quickLastTaskId }}</span>
        <button type="button" class="text-sm text-blue-600 hover:underline" @click="goTasks">去任务中心</button>
      </div>
    </div>

    <a-row :gutter="16">
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="模板总数" :value="totalTemplates" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="analyse 模板" :value="typeCounts.analyse ?? 0" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="collect_* 模板" :value="(typeCounts.collect_binance ?? 0) + (typeCounts.collect_uniswap ?? 0)" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <div class="text-xs text-[#57606a] dark:text-[#7d8590]">模板类型分布</div>
          <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-1">用于快速查看当前模板覆盖情况</div>
        </a-card>
      </a-col>
    </a-row>

    <div class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] p-4">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-medium text-[#24292f] dark:text-[#e6edf3]">类型分布</div>
        <button
          type="button"
          class="text-sm text-blue-600 hover:underline"
          :disabled="loading"
          @click="fetchTemplates"
        >
          刷新
        </button>
      </div>
      <div ref="chartRef" style="height: 260px;"></div>
    </div>

    <div class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] p-4">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="text-sm font-medium text-[#24292f] dark:text-[#e6edf3]">快捷运行</div>
          <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-1">
            选择一个模板并填写参数（overrides），点击运行即可创建任务。
          </div>
        </div>
        <button type="button" class="text-sm text-blue-600 hover:underline" @click="goTasks">任务中心</button>
      </div>

      <a-tabs size="small">
        <a-tab-pane key="collect_binance" tab="collect_binance">
          <a-row :gutter="12">
            <a-col :xs="24" :md="10">
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">模板</div>
              <a-select
                v-model:value="quickSelectedTemplateId.collect_binance"
                :options="templateOptionsByType.collect_binance"
                placeholder="选择 collect_binance 模板"
                style="width: 100%"
              />
            </a-col>
            <a-col :xs="24" :md="14">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="10">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">csv_path（可选）</div>
                  <a-input v-model:value="quickParams.collect_binance.csv_path" placeholder="/data/xxx.csv" />
                </a-col>
                <a-col :xs="12" :sm="7">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">import_percentage</div>
                  <a-input-number v-model:value="quickParams.collect_binance.import_percentage" :min="1" :max="100" style="width: 100%" />
                </a-col>
                <a-col :xs="12" :sm="7">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">chunk_size</div>
                  <a-input-number v-model:value="quickParams.collect_binance.chunk_size" :min="1" style="width: 100%" />
                </a-col>
              </a-row>
            </a-col>
          </a-row>
          <div class="mt-3">
            <a-button type="primary" :loading="quickLoading.collect_binance" @click="runQuick('collect_binance')">
              运行 collect_binance
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="collect_uniswap" tab="collect_uniswap">
          <a-row :gutter="12">
            <a-col :xs="24" :md="10">
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">模板</div>
              <a-select
                v-model:value="quickSelectedTemplateId.collect_uniswap"
                :options="templateOptionsByType.collect_uniswap"
                placeholder="选择 collect_uniswap 模板"
                style="width: 100%"
              />
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-3 mb-1">pool_address</div>
              <a-input v-model:value="quickParams.collect_uniswap.pool_address" placeholder="0x..." />
            </a-col>
            <a-col :xs="24" :md="14">
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-2">时间范围（可选，用于生成 start_ts/end_ts）</div>
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">start</div>
                  <input v-model="quickParams.collect_uniswap.start_time" type="datetime-local" class="w-full border rounded px-3 py-1.5 text-sm bg-white dark:bg-[#0d1117] border-[#d0d7de] dark:border-[#30363d]" />
                </a-col>
                <a-col :xs="24" :sm="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">end</div>
                  <input v-model="quickParams.collect_uniswap.end_time" type="datetime-local" class="w-full border rounded px-3 py-1.5 text-sm bg-white dark:bg-[#0d1117] border-[#d0d7de] dark:border-[#30363d]" />
                </a-col>
              </a-row>
            </a-col>
          </a-row>
          <div class="mt-3">
            <a-button type="primary" :loading="quickLoading.collect_uniswap" @click="runQuick('collect_uniswap')">
              运行 collect_uniswap
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="process_prices" tab="process_prices">
          <a-row :gutter="12">
            <a-col :xs="24" :md="10">
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">模板</div>
              <a-select
                v-model:value="quickSelectedTemplateId.process_prices"
                :options="templateOptionsByType.process_prices"
                placeholder="选择 process_prices 模板"
                style="width: 100%"
              />
            </a-col>
            <a-col :xs="24" :md="14">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="8">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">aggregation_interval</div>
                  <a-select
                    v-model:value="quickParams.process_prices.aggregation_interval"
                    style="width: 100%"
                    :options="[
                      { label: '1m', value: '1m' },
                      { label: '5m', value: '5m' },
                      { label: '15m', value: '15m' },
                      { label: '1h', value: '1h' },
                    ]"
                  />
                </a-col>
                <a-col :xs="12" :sm="8">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">overwrite</div>
                  <div class="pt-1">
                    <a-switch v-model:checked="quickParams.process_prices.overwrite" />
                  </div>
                </a-col>
              </a-row>
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-3 mb-2">时间范围（可选，会被转成 RFC3339）</div>
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">start</div>
                  <input v-model="quickParams.process_prices.start_time" type="datetime-local" class="w-full border rounded px-3 py-1.5 text-sm bg-white dark:bg-[#0d1117] border-[#d0d7de] dark:border-[#30363d]" />
                </a-col>
                <a-col :xs="24" :sm="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">end</div>
                  <input v-model="quickParams.process_prices.end_time" type="datetime-local" class="w-full border rounded px-3 py-1.5 text-sm bg-white dark:bg-[#0d1117] border-[#d0d7de] dark:border-[#30363d]" />
                </a-col>
              </a-row>
            </a-col>
          </a-row>
          <div class="mt-3">
            <a-button type="primary" :loading="quickLoading.process_prices" @click="runQuick('process_prices')">
              运行 process_prices
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="analyse" tab="analyse">
          <a-row :gutter="12">
            <a-col :xs="24" :md="10">
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">模板</div>
              <a-select
                v-model:value="quickSelectedTemplateId.analyse"
                :options="templateOptionsByType.analyse"
                placeholder="选择 analyse 模板"
                style="width: 100%"
              />
              <a-row :gutter="12" class="mt-3">
                <a-col :xs="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">batch_id</div>
                  <a-input-number v-model:value="quickParams.analyse.batch_id" :min="1" style="width: 100%" />
                </a-col>
                <a-col :xs="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">overwrite</div>
                  <div class="pt-1">
                    <a-switch v-model:checked="quickParams.analyse.overwrite" />
                  </div>
                  <div class="text-[11px] text-[#57606a] dark:text-[#7d8590] mt-1">
                    仅覆盖当前 <span class="font-mono">batch_id</span> 的历史结果
                  </div>
                </a-col>
              </a-row>
            </a-col>
            <a-col :xs="24" :md="14">
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-2">策略参数（strategy）</div>
              <a-row :gutter="12">
                <a-col :xs="12" :sm="8">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">profit_threshold</div>
                  <a-input-number v-model:value="quickParams.analyse.profit_threshold" :min="0" :step="0.1" style="width: 100%" />
                </a-col>
                <a-col :xs="12" :sm="8">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">time_delay_seconds</div>
                  <a-input-number v-model:value="quickParams.analyse.time_delay_seconds" :min="0" :step="1" style="width: 100%" />
                </a-col>
                <a-col :xs="24" :sm="8">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">initial_investment</div>
                  <a-input-number v-model:value="quickParams.analyse.initial_investment" :min="0" :step="100" style="width: 100%" />
                </a-col>
              </a-row>

              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-3 mb-2">时间范围（可选，写入 strategy.start / strategy.end）</div>
              <a-row :gutter="12">
                <a-col :xs="24" :sm="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">start</div>
                  <input v-model="quickParams.analyse.start_time" type="datetime-local" class="w-full border rounded px-3 py-1.5 text-sm bg-white dark:bg-[#0d1117] border-[#d0d7de] dark:border-[#30363d]" />
                </a-col>
                <a-col :xs="24" :sm="12">
                  <div class="text-xs text-[#57606a] dark:text-[#7d8590] mb-1">end</div>
                  <input v-model="quickParams.analyse.end_time" type="datetime-local" class="w-full border rounded px-3 py-1.5 text-sm bg-white dark:bg-[#0d1117] border-[#d0d7de] dark:border-[#30363d]" />
                </a-col>
              </a-row>
            </a-col>
          </a-row>
          <div class="mt-3">
            <a-button type="primary" :loading="quickLoading.analyse" @click="runQuick('analyse')">
              运行 analyse
            </a-button>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>

    <div class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d]">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-[#d0d7de] dark:divide-[#30363d] text-sm">
          <thead class="bg-[#f6f8fa] dark:bg-[#0d1117] text-[#57606a] dark:text-[#7d8590] text-xs uppercase">
            <tr>
              <th class="px-4 py-2 text-left">名称</th>
              <th class="px-4 py-2 text-left">任务类型</th>
              <th class="px-4 py-2 text-left">更新</th>
              <th class="px-4 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#d0d7de] dark:divide-[#30363d]">
            <tr v-for="item in templates" :key="item.id">
              <td class="px-4 py-2">{{ item.name }}</td>
              <td class="px-4 py-2 font-mono text-xs">{{ item.task_type }}</td>
              <td class="px-4 py-2 text-xs text-[#57606a] dark:text-[#7d8590]">{{ item.updated_at ?? '-' }}</td>
              <td class="px-4 py-2 text-right space-x-2">
                <button class="text-blue-600 hover:underline text-xs" @click="editTemplate(item)">
                  编辑
                </button>
                <button class="text-green-600 hover:underline text-xs" @click="runTemplate(item.id)">
                  运行
                </button>
                <button class="text-red-600 hover:underline text-xs" @click="deleteTemplate(item.id)">
                  删除
                </button>
              </td>
            </tr>
            <tr v-if="!loading && templates.length === 0">
              <td colspan="4" class="px-4 py-6 text-center text-[#57606a] dark:text-[#7d8590]">暂无模板</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="formVisible"
      class="fixed inset-0 bg-black/30 flex items-center justify-center z-10"
      @click.self="formVisible = false"
    >
      <div class="bg-white dark:bg-[#161b22] rounded-lg shadow-lg w-full max-w-lg p-6 space-y-4 border border-[#d0d7de] dark:border-[#30363d]">
        <h2 class="text-lg font-semibold">
          {{ editId ? '编辑模板' : '新建模板' }}
        </h2>
        <div class="space-y-2">
          <label class="text-sm text-[#57606a] dark:text-[#7d8590]">名称</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="请输入模板名称"
            class="w-full border rounded px-3 py-2 text-sm bg-white dark:bg-[#0d1117] text-[#24292f] dark:text-[#e6edf3] border-[#d0d7de] dark:border-[#30363d] placeholder:text-[#8c959f] dark:placeholder:text-[#7d8590]"
          />
        </div>
        <div class="space-y-2">
          <label class="text-sm text-[#57606a] dark:text-[#7d8590]">任务类型</label>
          <select
            v-model="form.task_type"
            class="w-full border rounded px-3 py-2 text-sm bg-white dark:bg-[#0d1117] text-[#24292f] dark:text-[#e6edf3] border-[#d0d7de] dark:border-[#30363d]"
          >
            <option value="collect_binance">collect_binance</option>
            <option value="collect_uniswap">collect_uniswap</option>
            <option value="process_prices">process_prices</option>
            <option value="analyse">analyse</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="text-sm text-[#57606a] dark:text-[#7d8590]">配置（JSON）</label>
          <textarea
            :value="formattedConfig"
            @input="handleConfigChange"
            rows="6"
            placeholder='例如：{"batch_id": 1, "overwrite": false, "strategy": {"profit_threshold": 10}}'
            class="w-full border rounded px-3 py-2 text-xs font-mono bg-white dark:bg-[#0d1117] text-[#24292f] dark:text-[#e6edf3] border-[#d0d7de] dark:border-[#30363d] placeholder:text-[#8c959f] dark:placeholder:text-[#7d8590]"
          />
          <p class="text-xs text-[#57606a] dark:text-[#7d8590]">
            根据任务类型填写对应字段，例如 collect_binance 需要 csv_path、import_percentage 等。
          </p>
        </div>
        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-[#57606a] dark:text-[#7d8590]"
            @click="formVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="px-4 py-2 bg-blue-600 text-white text-sm rounded"
            @click="submitForm"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
