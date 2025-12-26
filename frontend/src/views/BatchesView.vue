<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts';
import api from '../api';

interface BatchItem {
  id: number;
  name: string;
  description?: string;
  last_refreshed_at?: string;
  created_at?: string;
}

const batches = ref<BatchItem[]>([]);
const loading = ref(false);
const formVisible = ref(false);
const form = ref<{ name: string; description: string }>({ name: '', description: '' });
const selectedBatch = ref<BatchItem | null>(null);
const errorMessage = ref('');

const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const refreshedCount = computed(
  () => batches.value.filter((b) => Boolean(b.last_refreshed_at)).length,
);
const unrefreshedCount = computed(() => batches.value.length - refreshedCount.value);
const latestRefresh = computed(() => {
  const times = batches.value
    .map((b) => (b.last_refreshed_at ? new Date(b.last_refreshed_at).getTime() : NaN))
    .filter((t) => Number.isFinite(t)) as number[];
  if (!times.length) return '--';
  return new Date(Math.max(...times)).toLocaleString();
});

const fetchBatches = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getBatches();
    batches.value = data?.data ?? data ?? [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '批次列表获取失败';
  } finally {
    loading.value = false;
    nextTick(renderChart);
  }
};

const openCreate = () => {
  form.value = { name: '', description: '' };
  formVisible.value = true;
};

const createBatch = async () => {
  try {
    await api.createBatch(form.value);
    formVisible.value = false;
    await fetchBatches();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '创建批次失败';
  }
};

const refreshBatch = async (batch: BatchItem) => {
  if (!confirm('刷新批次会更新最后时间，确认操作？')) return;
  try {
    await api.updateBatch(batch.id, { name: batch.name, description: batch.description, refreshed: true });
    await fetchBatches();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '刷新失败';
  }
};

onMounted(fetchBatches);

const renderChart = () => {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);

  const now = Date.now();
  const rows = batches.value
    .slice()
    .sort((a, b) => (b.id ?? 0) - (a.id ?? 0))
    .slice(0, 12)
    .map((b) => {
      const ts = b.last_refreshed_at ? new Date(b.last_refreshed_at).getTime() : NaN;
      const days = Number.isFinite(ts) ? Math.max(0, (now - ts) / (1000 * 60 * 60 * 24)) : null;
      return { name: `#${b.id}`, days, refreshed: Number.isFinite(ts) };
    });

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params?.[0];
        const row = rows[p?.dataIndex ?? 0];
        if (!row) return '';
        return row.refreshed && row.days !== null
          ? `${row.name}<br/>距上次刷新：${row.days.toFixed(1)} 天`
          : `${row.name}<br/>未刷新`;
      },
    },
    toolbox: { feature: { saveAsImage: {} } },
    grid: { left: 44, right: 14, top: 18, bottom: 40 },
    xAxis: { type: 'category', data: rows.map((r) => r.name), axisLabel: { rotate: 20 } },
    yAxis: { type: 'value', name: 'days since refresh' },
    series: [
      {
        type: 'bar',
        data: rows.map((r) => (r.days === null ? 0 : Number(r.days.toFixed(2)))),
        itemStyle: {
          color: (p: any) => (rows[p.dataIndex]?.refreshed ? '#1890ff' : '#d9d9d9'),
        },
      },
    ],
  });
};

watch(
  () => batches.value,
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
        <h1 class="text-2xl font-semibold text-[#24292f] dark:text-[#e6edf3]">批次管理</h1>
        <p class="text-sm text-[#57606a] dark:text-[#7d8590]">查看批次信息并快速刷新。</p>
      </div>
      <button type="button" class="px-4 py-2 bg-indigo-600 text-white rounded text-sm" @click="openCreate">
        新建批次
      </button>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>

    <a-row :gutter="16">
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="总批次" :value="batches.length" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="已刷新" :value="refreshedCount" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="未刷新" :value="unrefreshedCount" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="6">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <div class="text-xs text-[#57606a] dark:text-[#7d8590]">最近刷新</div>
          <div class="text-sm text-[#24292f] dark:text-[#e6edf3] mt-1">{{ latestRefresh }}</div>
        </a-card>
      </a-col>
    </a-row>

    <div class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] p-4">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-medium text-[#24292f] dark:text-[#e6edf3]">刷新情况（最近 12 个批次）</div>
        <button type="button" class="text-xs text-blue-600 hover:underline" :disabled="loading" @click="fetchBatches">
          刷新数据
        </button>
      </div>
      <div ref="chartRef" style="height: 260px;"></div>
    </div>

    <div class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] divide-y divide-[#d0d7de] dark:divide-[#30363d]">
      <div
        v-for="batch in batches"
        :key="batch.id"
        class="p-4 flex items-center justify-between gap-4"
      >
        <div class="space-y-1">
          <div class="text-base font-medium">
            {{ batch.name }}
            <span class="text-xs text-[#57606a] dark:text-[#7d8590] ml-2">ID: {{ batch.id }}</span>
          </div>
          <div class="text-sm text-[#57606a] dark:text-[#7d8590]">{{ batch.description || '暂无描述' }}</div>
          <div class="text-xs text-[#57606a] dark:text-[#7d8590]">
            最近刷新：{{ batch.last_refreshed_at ?? '尚未刷新' }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="text-blue-600 text-xs hover:underline"
            @click="selectedBatch = batch"
          >
            查看
          </button>
          <button
            class="text-green-600 text-xs hover:underline"
            @click="refreshBatch(batch)"
          >
            刷新
          </button>
        </div>
      </div>
      <div v-if="!loading && batches.length === 0" class="p-6 text-center text-[#57606a] dark:text-[#7d8590] text-sm">
        暂无批次数据
      </div>
    </div>

    <div v-if="selectedBatch" class="bg-white dark:bg-[#161b22] rounded-lg shadow border border-[#d0d7de] dark:border-[#30363d] p-4 space-y-2">
      <h2 class="text-lg font-semibold">批次详情</h2>
      <div class="text-sm text-[#24292f] dark:text-[#e6edf3]">名称：{{ selectedBatch.name }}</div>
      <div class="text-sm text-[#24292f] dark:text-[#e6edf3]">描述：{{ selectedBatch.description || '-' }}</div>
      <div class="text-sm text-[#24292f] dark:text-[#e6edf3]">
        最近刷新：{{ selectedBatch.last_refreshed_at ?? '尚未刷新' }}
      </div>
    </div>

    <div
      v-if="formVisible"
      class="fixed inset-0 bg-black/30 flex items-center justify-center z-10"
      @click.self="formVisible = false"
    >
      <div class="bg-white dark:bg-[#161b22] rounded-lg shadow-lg w-full max-w-md p-6 space-y-4 border border-[#d0d7de] dark:border-[#30363d]">
        <h2 class="text-lg font-semibold">新建批次</h2>
        <div class="space-y-2">
          <label class="text-sm text-[#57606a] dark:text-[#7d8590]">名称</label>
          <input v-model="form.name" type="text" class="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div class="space-y-2">
          <label class="text-sm text-[#57606a] dark:text-[#7d8590]">描述</label>
          <textarea
            v-model="form.description"
            rows="3"
            class="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div class="flex justify-end gap-3">
          <button type="button" class="px-4 py-2 text-sm text-[#57606a] dark:text-[#7d8590]" @click="formVisible = false">
            取消
          </button>
          <button type="button" class="px-4 py-2 bg-blue-600 text-white text-sm rounded" @click="createBatch">
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
