<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import * as echarts from 'echarts';
import api, { type ReportPayload } from '../api';

interface ReportItem {
  id: number;
  batch_id: number;
  template_id?: number;
  format: string;
  file_path?: string;
  generated_at?: string;
}

const reports = ref<ReportItem[]>([]);
const loading = ref(false);
const errorMessage = ref('');
const form = reactive<ReportPayload>({
  batch_id: 1,
  template_id: undefined,
  format: 'PDF',
  file_path: '',
});
const creating = ref(false);

const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const totalReports = computed(() => reports.value.length);
const latestGeneratedAt = computed(() => {
  const times = reports.value
    .map((r) => (r.generated_at ? new Date(r.generated_at).getTime() : NaN))
    .filter((t) => Number.isFinite(t)) as number[];
  if (!times.length) return '--';
  return new Date(Math.max(...times)).toLocaleString();
});
const formatCounts = computed(() => {
  const counts: Record<string, number> = {};
  for (const r of reports.value) {
    const key = r.format ?? 'UNKNOWN';
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
});

const fetchReports = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getReports();
    reports.value = data?.data ?? data ?? [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '报告列表获取失败';
  } finally {
    loading.value = false;
    nextTick(renderChart);
  }
};

const submitReport = async () => {
  creating.value = true;
  errorMessage.value = '';
  try {
    await api.createReport(form);
    await fetchReports();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '生成报告失败';
  } finally {
    creating.value = false;
  }
};

onMounted(fetchReports);

const renderChart = () => {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);

  const map = new Map<number, number>();
  for (const r of reports.value) {
    if (typeof r.batch_id !== 'number') continue;
    map.set(r.batch_id, (map.get(r.batch_id) ?? 0) + 1);
  }
  const batchIds = Array.from(map.keys()).sort((a, b) => a - b).slice(0, 12);
  const labels = batchIds.map((id) => `#${id}`);
  const values = batchIds.map((id) => map.get(id) ?? 0);

  chart.setOption({
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: {} } },
    grid: { left: 44, right: 14, top: 18, bottom: 40 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 25 } },
    yAxis: { type: 'value', name: 'reports' },
    series: [{ type: 'bar', data: values, itemStyle: { color: '#52c41a' } }],
  });
};

watch(
  () => reports.value,
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
    <header>
      <h1 class="text-2xl font-semibold text-[#24292f] dark:text-[#e6edf3]">报告中心</h1>
      <p class="text-sm text-[#57606a] dark:text-[#7d8590]">生成与查看批次报告。</p>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>

    <a-row :gutter="16">
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="总报告" :value="totalReports" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="PDF" :value="formatCounts.PDF ?? 0" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="HTML/MD" :value="(formatCounts.HTML ?? 0) + (formatCounts.Markdown ?? 0)" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <div class="text-xs text-[#57606a] dark:text-[#7d8590]">最近生成</div>
          <div class="text-sm text-[#24292f] dark:text-[#e6edf3] mt-1">{{ latestGeneratedAt }}</div>
        </a-card>
      </a-col>
    </a-row>

    <section class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] p-4">
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-sm font-medium text-[#24292f] dark:text-[#e6edf3]">报告分布（按批次）</h2>
        <button
          type="button"
          class="text-sm text-blue-600 hover:underline"
          :disabled="loading"
          @click="fetchReports"
        >
          刷新
        </button>
      </div>
      <div ref="chartRef" style="height: 260px;"></div>
    </section>

    <section class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] p-4 space-y-4">
      <h2 class="text-lg font-medium">生成报告</h2>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <label class="text-sm text-[#57606a] dark:text-[#7d8590]">
          批次 ID
          <input
            v-model.number="form.batch_id"
            type="number"
            min="1"
            class="w-full border rounded px-3 py-2 text-sm mt-1"
          />
        </label>
        <label class="text-sm text-[#57606a] dark:text-[#7d8590]">
          模板 ID（可选）
          <input
            v-model.number="form.template_id"
            type="number"
            min="1"
            class="w-full border rounded px-3 py-2 text-sm mt-1"
          />
        </label>
        <label class="text-sm text-[#57606a] dark:text-[#7d8590]">
          格式
          <select v-model="form.format" class="w-full border rounded px-3 py-2 text-sm mt-1">
            <option value="PDF">PDF</option>
            <option value="HTML">HTML</option>
            <option value="Markdown">Markdown</option>
          </select>
        </label>
        <label class="text-sm text-[#57606a] dark:text-[#7d8590]">
          文件路径（可选）
          <input
            v-model="form.file_path"
            type="text"
            class="w-full border rounded px-3 py-2 text-sm mt-1"
          />
        </label>
      </div>
      <button
        type="button"
        class="px-4 py-2 bg-blue-600 text-white text-sm rounded"
        :disabled="creating"
        @click="submitReport"
      >
        {{ creating ? '生成中...' : '生成报告' }}
      </button>
    </section>

    <section class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d]">
      <div class="p-4 border-b flex items-center justify-between">
        <h2 class="text-lg font-medium">报告列表</h2>
        <button
          type="button"
          class="text-sm text-blue-600 hover:underline"
          :disabled="loading"
          @click="fetchReports"
        >
          刷新
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-[#d0d7de] dark:divide-[#30363d] text-sm">
          <thead class="bg-[#f6f8fa] dark:bg-[#0d1117] text-[#57606a] dark:text-[#7d8590] text-xs uppercase">
            <tr>
              <th class="px-4 py-2 text-left">ID</th>
              <th class="px-4 py-2 text-left">批次</th>
              <th class="px-4 py-2 text-left">模板</th>
              <th class="px-4 py-2 text-left">格式</th>
              <th class="px-4 py-2 text-left">生成时间</th>
              <th class="px-4 py-2 text-left">文件</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#d0d7de] dark:divide-[#30363d]">
            <tr v-for="report in reports" :key="report.id">
              <td class="px-4 py-2">{{ report.id }}</td>
              <td class="px-4 py-2">{{ report.batch_id }}</td>
              <td class="px-4 py-2">{{ report.template_id ?? '-' }}</td>
              <td class="px-4 py-2">{{ report.format }}</td>
              <td class="px-4 py-2">{{ report.generated_at ?? '-' }}</td>
              <td class="px-4 py-2">
                <a
                  v-if="report.file_path"
                  :href="report.file_path"
                  target="_blank"
                  class="text-blue-600 text-xs hover:underline"
                >
                  下载
                </a>
                <span v-else class="text-[#57606a] dark:text-[#7d8590] text-xs">—</span>
              </td>
            </tr>
            <tr v-if="!loading && reports.length === 0">
              <td colspan="6" class="px-4 py-6 text-center text-[#57606a] dark:text-[#7d8590]">暂无报告</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
