<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';
import {
  TrendingUp,
  DollarSign,
  Activity,
  ChevronLeft,
  ChevronRight,
  Loader2,
  BarChart3,
  X,
  Clock,
  ArrowRightLeft,
  LineChart,
  Binary
} from 'lucide-vue-next';
import api from '../../api';

type Theme = 'light' | 'dark';
type SortField = 'timestamp' | 'netProfit' | 'grossProfit';
type SortDirection = 'asc' | 'desc';

interface Props {
  theme: Theme;
}

interface RiskMetrics {
  risk_score: number;
  volatility: number;
  estimated_slippage_pct: number;
  market_volume_eth: number;
}

interface ApiOpportunity {
  id: number;
  batch_id?: number;
  buy_platform: string;
  sell_platform: string;
  buy_price: number;
  sell_price: number;
  profit_usdt: number;
  risk_metrics: RiskMetrics;
  created_at?: string;
  timestamp?: string | number;
  details?: {
    block_time?: string;
    experiment_id?: string;
  };
}

interface Batch {
  id: number;
  name: string;
  description?: string;
  last_refreshed_at?: string;
}

const props = defineProps<Props>();

// --- Refs ---
const comparisonChartRef = ref<HTMLDivElement | null>(null); // 新增：对比图容器
const scatterChartRef = ref<HTMLDivElement | null>(null);
const distChartRef = ref<HTMLDivElement | null>(null);
const pieChartRef = ref<HTMLDivElement | null>(null);
const modalChartRef = ref<HTMLDivElement | null>(null);

let comparisonChartInstance: echarts.ECharts | null = null; // 新增：对比图实例
let scatterChartInstance: echarts.ECharts | null = null;
let distChartInstance: echarts.ECharts | null = null;
let pieChartInstance: echarts.ECharts | null = null;
let modalChartInstance: echarts.ECharts | null = null;

const itemsPerPage = 10;
const currentPage = ref(1);
const sortField = ref<SortField>('netProfit');
const sortDirection = ref<SortDirection>('desc');
const opportunities = ref<ApiOpportunity[]>([]);
const opportunitiesLoaded = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');
const unsupportedNotice = ref('');
const batches = ref<Batch[]>([]);
const batchesLoading = ref(false);
const batchError = ref('');
const openedBatchIds = ref<number[]>([]);
const selectedOpp = ref<ApiOpportunity | null>(null);
const modalChartLoading = ref(false);
const showTimestamp = ref(false);

const isDark = computed(() => props.theme === 'dark');
const textColor = computed(() => isDark.value ? '#e6edf3' : '#24292f');
const secondaryTextColor = computed(() => isDark.value ? '#7d8590' : '#57606a');
const backgroundColor = computed(() => isDark.value ? '#161b22' : 'white');
const borderColor = computed(() => isDark.value ? '#30363d' : '#d0d7de');

const getRiskColor = (score: number) => {
  if (score >= 80) return 'text-[#3fb950]'; // Green
  if (score >= 60) return 'text-[#d29922]'; // Orange
  return 'text-[#f85149]'; // Red
};

const filteredOpportunities = computed(() => {
  if (!openedBatchIds.value.length) return [];
  return opportunities.value.filter(
    (item) => typeof item.batch_id === 'number' && openedBatchIds.value.includes(item.batch_id),
  );
});

// --- 辅助函数 ---
const getTimeFromItem = (item: ApiOpportunity): number => {
  const raw = item.details?.block_time || item.created_at || item.timestamp;
  if (!raw) return Date.now();
  if (typeof raw === 'number') {
    return raw < 10000000000 ? raw * 1000 : raw;
  }
  return new Date(raw).getTime();
};

const calculateRoi = (item: ApiOpportunity) => {
  if (!item.buy_price) return 0;
  return ((item.profit_usdt / item.buy_price) * 100).toFixed(2);
};

const formatFullTime = (ts: number | string | undefined) => {
  if (!ts) return '--';
  const num = typeof ts === 'string' ? new Date(ts).getTime() : ts;
  if (Number.isNaN(num)) return '--';
  return new Date(num).toLocaleString();
};

const formatCurrency = (value: number) => `$${value.toFixed(2)}`;

// --- 弹窗逻辑 ---
const openDetails = (item: ApiOpportunity) => {
  selectedOpp.value = item;
  showTimestamp.value = false;
  nextTick(() => loadModalChart(item));
};

const closeDetails = () => {
  selectedOpp.value = null;
  if (modalChartInstance) {
    modalChartInstance.dispose();
    modalChartInstance = null;
  }
};

const toggleTimestamp = () => {
  showTimestamp.value = !showTimestamp.value;
  if (modalChartInstance) {
    modalChartInstance.setOption({
      xAxis: {
        axisLabel: {
          hideOverlap: true,
          formatter: showTimestamp.value ? (value: number) => `${value}` : undefined
        }
      }
    });
  }
};

// --- ECharts: 加载弹窗内的迷你价格图 ---
const loadModalChart = async (item: ApiOpportunity) => {
  if (!modalChartRef.value) return;
  modalChartLoading.value = true;
  if (modalChartInstance) modalChartInstance.dispose();
  modalChartInstance = echarts.init(modalChartRef.value);

  const centerTime = getTimeFromItem(item);
  const range = 4 * 60 * 60 * 1000; 
  const start = centerTime - range;
  const end = centerTime + range;
  const buyPrice = Number(item.buy_price);
  const sellPrice = Number(item.sell_price);

  try {
    const { data } = await api.getPriceComparisonData({ startTime: start, endTime: end });
    const payload = data?.data ?? {};
    const uniswapData = (payload.uniswap || []).map((p: any) => [p[0], Number(p[1])]);
    const binanceData = (payload.binance || []).map((p: any) => [p[0], Number(p[1])]);

    const buyPoint = {
      name: 'Buy',
      value: [centerTime, buyPrice],
      itemStyle: { color: '#3fb950', borderColor: isDark.value ? '#0d1117' : '#ffffff', borderWidth: 2, shadowBlur: 5, shadowColor: 'rgba(0,0,0,0.3)' },
      label: { 
        show: true, position: 'bottom', formatter: () => `{b|BUY}\n{p|${item.buy_platform}}`, 
        rich: { b: { fontWeight: 'bold', color: '#3fb950', fontSize: 11, lineHeight: 14, align: 'center' }, p: { color: secondaryTextColor.value, fontSize: 10, align: 'center' } },
        backgroundColor: backgroundColor.value, padding: [4, 8], borderRadius: 4, borderColor: '#3fb950', borderWidth: 1
      }
    };

    const sellPoint = {
      name: 'Sell',
      value: [centerTime, sellPrice],
      itemStyle: { color: '#f85149', borderColor: isDark.value ? '#0d1117' : '#ffffff', borderWidth: 2, shadowBlur: 5, shadowColor: 'rgba(0,0,0,0.3)' },
      label: { 
        show: true, position: 'top', formatter: () => `{b|SELL}\n{p|${item.sell_platform}}`,
        rich: { b: { fontWeight: 'bold', color: '#f85149', fontSize: 11, lineHeight: 14, align: 'center' }, p: { color: secondaryTextColor.value, fontSize: 10, align: 'center' } },
        backgroundColor: backgroundColor.value, padding: [4, 8], borderRadius: 4, borderColor: '#f85149', borderWidth: 1
      }
    };

    const spreadLineData = [[{ coord: [centerTime, buyPrice], symbol: 'none' }, { coord: [centerTime, sellPrice], symbol: 'none' }]];

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      title: { text: 'Arbitrage Execution Context', left: 'center', textStyle: { color: secondaryTextColor.value, fontSize: 12, fontWeight: 'normal' } },
      toolbox: { show: true, feature: { dataZoom: { yAxisIndex: 'none' }, restore: {} }, iconStyle: { borderColor: secondaryTextColor.value }, right: 20, top: 0 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } }, backgroundColor: backgroundColor.value, borderColor: borderColor.value, textStyle: { color: textColor.value } },
      grid: { top: 60, bottom: 60, left: 60, right: 40 },
      xAxis: { 
        type: 'time', 
        axisLine: { lineStyle: { color: borderColor.value } },
        axisLabel: { color: secondaryTextColor.value, fontSize: 10, hideOverlap: true, formatter: showTimestamp.value ? (value: number) => `${value}` : undefined },
        splitLine: { show: false }
      },
      yAxis: { type: 'value', scale: true, axisLabel: { color: secondaryTextColor.value, fontSize: 10 }, splitLine: { lineStyle: { type: 'dashed', opacity: 0.1 } } },
      dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'filter' }, { type: 'slider', xAxisIndex: 0, bottom: 20, height: 20, handleSize: '80%', borderColor: borderColor.value, textStyle: { color: secondaryTextColor.value } }],
      series: [
        { name: 'Uniswap V3', type: 'line', showSymbol: false, data: uniswapData, itemStyle: { color: '#58a6ff' }, lineStyle: { width: 1.5, opacity: 0.6 }, z: 1 },
        { name: 'Binance', type: 'line', showSymbol: false, data: binanceData, itemStyle: { color: '#f78166' }, lineStyle: { width: 1.5, opacity: 0.6 }, z: 1 },
        {
          type: 'scatter', symbolSize: 10, z: 10, data: [buyPoint, sellPoint],
          markLine: { silent: true, symbol: 'none', lineStyle: { color: textColor.value, type: 'dashed', width: 1, opacity: 0.5 }, data: spreadLineData }
        }
      ] as any
    };
    modalChartInstance.setOption(option);
  } catch (e) {
    console.error("Failed to load modal chart", e);
    modalChartInstance.setOption({ title: { text: 'Unable to load chart data', left: 'center', top: 'center', textStyle: { color: '#f85149', fontSize: 14 } } });
  } finally {
    modalChartLoading.value = false;
  }
};

// --- ECharts: 实验对比图 (Batch Comparison) ---
const renderComparisonChart = () => {
  if (!comparisonChartRef.value) return;
  // 如果只选了一个批次，没必要对比，不显示
  if (openedBatchIds.value.length < 2) {
    if (comparisonChartInstance) {
      comparisonChartInstance.dispose();
      comparisonChartInstance = null;
    }
    return;
  }

  if (!comparisonChartInstance) comparisonChartInstance = echarts.init(comparisonChartRef.value);

  // 1. 聚合数据
  const batchStats = openedBatchIds.value.map(batchId => {
    const batchOps = opportunities.value.filter(o => o.batch_id === batchId);
    const totalProfit = batchOps.reduce((sum, o) => sum + (o.profit_usdt || 0), 0);
    const count = batchOps.length;
    const avgProfit = count > 0 ? totalProfit / count : 0;
    // 获取批次名称
    const batch = batches.value.find(b => b.id === batchId);
    const name = batch ? (batch.name || `Batch #${batchId}`) : `Batch #${batchId}`;
    
    return { name, totalProfit, avgProfit, count };
  });

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    title: { 
      text: 'Experiment Comparison', 
      left: 'center', 
      textStyle: { color: textColor.value, fontSize: 14 } 
    },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 30, textStyle: { color: secondaryTextColor.value } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: batchStats.map(b => b.name),
      axisLabel: { color: secondaryTextColor.value, interval: 0, rotate: 15 }
    },
    yAxis: [
      { 
        type: 'value', 
        name: 'Profit (USDT)', 
        position: 'left', 
        axisLabel: { color: secondaryTextColor.value },
        splitLine: { lineStyle: { type: 'dashed', opacity: 0.2 } } 
      },
      { 
        type: 'value', 
        name: 'Count', 
        position: 'right', 
        axisLabel: { color: secondaryTextColor.value },
        splitLine: { show: false } 
      }
    ],
    series: [
      {
        name: 'Total Profit',
        type: 'bar',
        data: batchStats.map(b => b.totalProfit),
        itemStyle: { color: '#238636' }
      },
      {
        name: 'Avg Profit',
        type: 'bar',
        data: batchStats.map(b => b.avgProfit),
        itemStyle: { color: '#e3b341' }
      },
      {
        name: 'Opp Count',
        type: 'line',
        yAxisIndex: 1,
        data: batchStats.map(b => b.count),
        itemStyle: { color: '#58a6ff' },
        smooth: true
      }
    ]
  };
  
  comparisonChartInstance.setOption(option);
};

// --- ECharts: 常规分析图表 ---
const renderCharts = () => {
  if (!scatterChartRef.value || !distChartRef.value || !pieChartRef.value) return;
  const dataset = filteredOpportunities.value;
  
  if (!scatterChartInstance) scatterChartInstance = echarts.init(scatterChartRef.value);
  if (!distChartInstance) distChartInstance = echarts.init(distChartRef.value);
  if (!pieChartInstance) pieChartInstance = echarts.init(pieChartRef.value);

  if (dataset.length === 0) {
    scatterChartInstance.clear();
    distChartInstance.clear();
    pieChartInstance.clear();
    return;
  }

  // 1. 散点图
  const scatterData = dataset.map(item => ({
    value: [getTimeFromItem(item), item.profit_usdt, item.buy_platform, item.sell_platform, item.buy_price, item.sell_price, item.id, item.batch_id],
    itemStyle: { color: (item.buy_platform && item.buy_platform.toLowerCase().includes('binance')) ? '#f78166' : '#58a6ff', opacity: 0.8 }
  })).filter(d => !Number.isNaN(d.value[0]));

  const profits = dataset.map(d => d.profit_usdt).sort((a, b) => a - b);
  const p98Index = Math.floor(profits.length * 0.98);
  const p98Value = profits[p98Index] ?? (profits[profits.length - 1] ?? 100);
  const zoomEnd = Math.max(p98Value * 1.5, 10);

  scatterChartInstance.setOption({
    backgroundColor: 'transparent',
    title: { text: 'Batch Timeline', left: 'center', textStyle: { color: textColor.value, fontSize: 14 } },
    tooltip: {
      trigger: 'item', backgroundColor: backgroundColor.value, borderColor: borderColor.value, textStyle: { color: textColor.value }, confine: true,
      formatter: (params: any) => {
        const v = params.value;
        const d = new Date(v[0]).toLocaleString();
        return `<div style="font-size:12px;"><div style="font-weight:bold;">#${v[6]}</div><div>${d}</div><div style="color:#3fb950;">+$${v[1].toFixed(2)}</div></div>`;
      }
    },
    grid: { left: '3%', right: '8%', bottom: '10%', top: '20%', containLabel: true },
    xAxis: { type: 'time', axisLabel: { color: secondaryTextColor.value }, splitLine: { show: false } },
    yAxis: { name: 'Profit', type: 'value', axisLabel: { color: secondaryTextColor.value }, splitLine: { lineStyle: { type: 'dashed', opacity: 0.2 } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', yAxisIndex: 0, right: 0, width: 15, startValue: 0, endValue: zoomEnd, handleSize: '80%' }],
    series: [{ type: 'scatter', symbolSize: 8, large: false, emphasis: { focus: 'self', scale: true }, data: scatterData }]
  }, { notMerge: true });

  // 2. 分布图
  const p98Val = profits[p98Index] ?? 0;
  const maxVal = profits[profits.length - 1] ?? 0;
  const visualMax = p98Val > 0 ? p98Val : (maxVal > 0 ? maxVal : 10);
  const binCount = 20;
  const step = visualMax / binCount;
  const bins = new Array(binCount + 1).fill(0);
  const labels: string[] = [];
  for (let i = 0; i < binCount; i++) {
    const start = i * step;
    const end = start + step;
    labels.push(`${start.toFixed(2)}-${end.toFixed(2)}`);
  }
  labels.push(`>${visualMax.toFixed(2)}`);
  profits.forEach(p => {
    if (p > visualMax) bins[binCount]++;
    else {
      const index = Math.min(Math.floor(p / step), binCount - 1);
      if (index >= 0) bins[index]++;
    }
  });
  distChartInstance.setOption({
    backgroundColor: 'transparent',
    title: { text: 'Profit Dist', left: 'center', textStyle: { color: textColor.value, fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 45, color: secondaryTextColor.value } },
    yAxis: { type: 'value', axisLabel: { color: secondaryTextColor.value } },
    series: [{ type: 'bar', data: bins, itemStyle: { color: '#238636' } }]
  });

  // 3. 饼图
  const stats: Record<string, number> = {};
  dataset.forEach(o => {
    const key = `${o.buy_platform} → ${o.sell_platform}`;
    stats[key] = (stats[key] || 0) + 1;
  });
  const pieData = Object.keys(stats).map(k => ({ name: k, value: stats[k] }));
  pieChartInstance.setOption({
    backgroundColor: 'transparent',
    title: { text: 'Path Share', left: 'center', textStyle: { color: textColor.value, fontSize: 14 } },
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '65%'], label: { show: true, position: 'outside', formatter: '{b}\n{d}%', color: secondaryTextColor.value }, data: pieData }]
  });
};

// 监听
watch([filteredOpportunities, () => props.theme], () => { 
  nextTick(() => {
    renderCharts();
    renderComparisonChart(); // 同时更新对比图
  });
}, { deep: true });

const handleResize = () => { 
  [scatterChartInstance, distChartInstance, pieChartInstance, modalChartInstance, comparisonChartInstance].forEach(c => c?.resize()); 
};
onMounted(() => { fetchBatches(); window.addEventListener('resize', handleResize); });
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); [scatterChartInstance, distChartInstance, pieChartInstance, modalChartInstance, comparisonChartInstance].forEach(c => c?.dispose()); });

// --- Table Logic ---
const sortedFilteredOpportunities = computed(() => {
  const list = [...filteredOpportunities.value];
  if (sortField.value === 'netProfit') {
    list.sort((a, b) => {
      const diff = (a.profit_usdt ?? 0) - (b.profit_usdt ?? 0);
      return sortDirection.value === 'asc' ? diff : -diff;
    });
  }
  return list;
});
const paginatedOpportunities = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return sortedFilteredOpportunities.value.slice(start, start + itemsPerPage);
});
const filteredTotal = computed(() => sortedFilteredOpportunities.value.length);
const totalPages = computed(() => filteredTotal.value ? Math.max(1, Math.ceil(filteredTotal.value / itemsPerPage)) : 1);
const stats = computed(() => {
  const profits = filteredOpportunities.value.map((item) => item.profit_usdt ?? 0);
  const total = filteredTotal.value;
  const maxProfit = profits.length ? Math.max(...profits) : 0;
  const totalProfit = profits.reduce((sum, value) => sum + value, 0);
  const avgProfit = profits.length ? totalProfit / profits.length : 0;
  return { totalOpportunities: total, maxProfit, avgProfit, totalPotentialProfit: totalProfit };
});
const fetchBatches = async () => {
  batchesLoading.value = true;
  try {
    const { data } = await api.getBatches();
    batches.value = data?.data ?? data ?? [];
  } catch (error: any) { batchError.value = error?.message ?? '批次列表获取失败'; } finally { batchesLoading.value = false; }
};
const fetchAllOpportunities = async () => {
  isLoading.value = true;
  try {
    const aggregated: ApiOpportunity[] = [];
    const pageSize = 200;
    let page = 1;
    let total = Number.POSITIVE_INFINITY;
    while (aggregated.length < total) {
      const { data } = await api.getOpportunities({ page, limit: pageSize, sort_by: 'profit_usdt', order: 'desc' });
      const payload = data?.data;
      const items: ApiOpportunity[] = payload?.items ?? [];
      const pagination = payload?.pagination;
      if (pagination?.total) total = pagination.total;
      aggregated.push(...items);
      if (!items.length || aggregated.length >= total) break;
      page += 1;
    }
    opportunities.value = aggregated;
    opportunitiesLoaded.value = true;
  } catch (error: any) { errorMessage.value = error?.message ?? '套利机会列表获取失败'; } finally { isLoading.value = false; }
};
const ensureOpportunitiesLoaded = async () => { if (opportunitiesLoaded.value || isLoading.value) return; await fetchAllOpportunities(); };
const isBatchOpened = (id: number) => openedBatchIds.value.includes(id);
const toggleBatch = async (batchId: number) => {
  if (isBatchOpened(batchId)) { openedBatchIds.value = openedBatchIds.value.filter((id) => id !== batchId); return; }
  await ensureOpportunitiesLoaded();
  openedBatchIds.value = [...openedBatchIds.value, batchId];
};
const openedBatches = computed(() => batches.value.filter((batch) => openedBatchIds.value.includes(batch.id)));
const handleSort = (field: SortField) => { if (field !== 'netProfit') return; sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'; };
const goToPage = (page: number) => { currentPage.value = Math.min(Math.max(page, 1), totalPages.value); };
const paginationRange = computed(() => {
  const pages = totalPages.value;
  if (pages <= 5) return Array.from({ length: pages }, (_, i) => i + 1);
  if (currentPage.value <= 3) return [1, 2, 3, 4, 5];
  if (currentPage.value >= pages - 2) return [pages - 4, pages - 3, pages - 2, pages - 1, pages];
  return [currentPage.value - 2, currentPage.value - 1, currentPage.value, currentPage.value + 1, currentPage.value + 2];
});
const showingRange = computed(() => {
  if (!filteredTotal.value) return { start: 0, end: 0 };
  const start = (currentPage.value - 1) * itemsPerPage + 1;
  const end = Math.min(currentPage.value * itemsPerPage, filteredTotal.value);
  return { start, end };
});
watch(filteredOpportunities, () => { currentPage.value = 1; });
watch(() => totalPages.value, (pages) => { if (currentPage.value > pages) currentPage.value = pages; });
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-md border p-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
      <div class="flex items-start justify-between mb-3">
        <div>
          <h3 class="text-sm font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">批次筛选</h3>
          <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">先选择一个或多个批次后再加载套利机会。</p>
        </div>
        <button type="button" class="text-xs px-3 py-1 rounded border" :class="isDark ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff]' : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da]'" @click="fetchBatches" :disabled="batchesLoading">{{ batchesLoading ? '加载中...' : '刷新批次' }}</button>
      </div>
      <div class="flex flex-wrap gap-2 mb-3" v-if="batches.length">
        <button v-for="batch in batches" :key="batch.id" type="button" class="px-3 py-1 rounded text-xs border transition-colors" :class="isBatchOpened(batch.id) ? 'bg-[#1f6feb] border-[#1f6feb] text-white' : (isDark ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff]' : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da]')" @click="toggleBatch(batch.id)">{{ batch.name }} (#{{ batch.id }})</button>
      </div>
      <p v-else-if="!batchesLoading" class="text-xs text-gray-500">暂无批次。</p>
      <div v-if="openedBatches.length" class="flex flex-wrap gap-2 text-xs">
        <span class="text-gray-500">已打开批次：</span>
        <button v-for="batch in openedBatches" :key="`opened-${batch.id}`" type="button" class="px-2 py-1 rounded-full border flex items-center gap-1" :class="isDark ? 'border-[#30363d] text-[#e6edf3]' : 'border-[#d0d7de] text-[#24292f]'" @click="toggleBatch(batch.id)">{{ batch.name }} (#{{ batch.id }}) <X class="w-3 h-3" /></button>
      </div>
    </div>

    <div v-if="openedBatchIds.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="rounded-md border p-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between mb-2"><span class="text-xs text-gray-500">Total</span><Activity class="w-4 h-4 text-[#58a6ff]" /></div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ stats.totalOpportunities }}</div>
      </div>
      <div class="rounded-md border p-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between mb-2"><span class="text-xs text-gray-500">Max Profit</span><TrendingUp class="w-4 h-4 text-[#3fb950]" /></div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ formatCurrency(stats.maxProfit) }}</div>
      </div>
      <div class="rounded-md border p-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between mb-2"><span class="text-xs text-gray-500">Avg Profit</span><DollarSign class="w-4 h-4 text-[#d29922]" /></div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ formatCurrency(stats.avgProfit) }}</div>
      </div>
      <div class="rounded-md border p-4" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
        <div class="flex items-center justify-between mb-2"><span class="text-xs text-gray-500">Potential</span><TrendingUp class="w-4 h-4 text-[#bc8cff]" /></div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">{{ formatCurrency(stats.totalPotentialProfit) }}</div>
      </div>
    </div>

    <div v-if="openedBatchIds.length > 1" class="rounded-md border p-4 h-[350px]" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
      <div ref="comparisonChartRef" class="w-full h-full"></div>
    </div>

    <div v-if="openedBatchIds.length && filteredTotal > 0" class="space-y-4 pt-2">
      <div class="flex items-center gap-2 pb-2 border-b" :class="isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'">
         <BarChart3 class="w-5 h-5" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'" />
         <h2 class="text-lg font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Batch Analytics</h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2 rounded-md border p-4 h-[350px]" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"><div ref="scatterChartRef" class="w-full h-full"></div></div>
        <div class="rounded-md border p-4 h-[350px]" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"><div ref="pieChartRef" class="w-full h-full"></div></div>
        <div class="lg:col-span-3 rounded-md border p-4 h-[300px]" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"><div ref="distChartRef" class="w-full h-full"></div></div>
      </div>
    </div>

    <div class="rounded-md border overflow-hidden" :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead :class="isDark ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]'">
            <tr :class="isDark ? 'border-b border-[#30363d]' : 'border-b border-[#d0d7de]'">
              <th class="px-4 py-3 text-left text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                ID
              </th>
              <th class="px-4 py-3 text-left text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Buy Platform
              </th>
              <th class="px-4 py-3 text-left text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Sell Platform
              </th>
              <th class="px-4 py-3 text-right text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Buy Price
              </th>
              <th class="px-4 py-3 text-right text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Sell Price
              </th>
              <th class="px-4 py-3 text-center text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Risk Score
              </th>
              <th
                class="px-4 py-3 text-right text-xs cursor-pointer"
                :class="isDark ? 'text-[#7d8590] hover:text-[#58a6ff]' : 'text-[#57606a] hover:text-[#0969da]'"
                @click="handleSort('netProfit')"
              >
                <span class="flex items-center justify-end gap-1">
                  Net Profit
                  <svg
                    class="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="m8 7 4-4 4 4m0 10-4 4-4-4" />
                  </svg>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!openedBatchIds.length">
              <td colspan="7" class="px-4 py-6 text-center text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                请选择左侧批次以查看套利数据。
              </td>
            </tr>
            <tr v-else-if="isLoading">
              <td colspan="7" class="px-4 py-6 text-center">
                <Loader2 class="w-4 h-4 inline-block animate-spin mr-2 text-[#58a6ff]" />
                <span :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">加载中...</span>
              </td>
            </tr>
            <tr
              v-else-if="!filteredTotal"
              :class="['border-b', isDark ? 'border-[#21262d]' : 'border-[#d0d7de]']"
            >
              <td colspan="7" class="px-4 py-6 text-center text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                所选批次暂未生成套利机会。
              </td>
            </tr>
            <tr
              v-else
              v-for="opportunity in paginatedOpportunities"
              :key="`${opportunity.batch_id}-${opportunity.id}`"
              class="border-b transition-colors cursor-pointer"
              :class="isDark ? 'border-[#21262d] hover:bg-[#0d1117]' : 'border-[#d0d7de] hover:bg-[#f6f8fa]'"
              @click="openDetails(opportunity)" 
            >
              <td class="px-4 py-3 text-sm" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                {{ opportunity.id }}
              </td>
              <td class="px-4 py-3 text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                {{ opportunity.buy_platform || '--' }}
              </td>
              <td class="px-4 py-3 text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                {{ opportunity.sell_platform || '--' }}
              </td>
              <td class="px-4 py-3 text-sm text-right" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                {{ formatCurrency(opportunity.buy_price ?? 0) }}
              </td>
              <td class="px-4 py-3 text-sm text-right" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                {{ formatCurrency(opportunity.sell_price ?? 0) }}
              </td>
              <td class="px-4 py-3 text-sm text-center">
                <div>
                  <span class="font-bold" :class="getRiskColor(opportunity.risk_metrics.risk_score)">
                    {{ opportunity.risk_metrics.risk_score }}
                  </span>
                  <div class="text-[10px]" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                    Slippage: {{ opportunity.risk_metrics.estimated_slippage_pct.toFixed(2) }}%
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-right text-[#3fb950]">
                {{ formatCurrency(opportunity.profit_usdt ?? 0) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-4 py-3 border-t flex items-center justify-between" :class="isDark ? 'border-[#30363d] bg-[#0d1117]' : 'border-[#d0d7de] bg-[#f6f8fa]'">
          <div class="text-xs text-gray-500">Showing {{ showingRange.start }}-{{ showingRange.end }} of {{ filteredTotal }}</div>
          <div class="flex items-center gap-1">
             <button class="p-1.5 border rounded" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)"><ChevronLeft class="w-4 h-4"/></button>
             <button v-for="page in paginationRange" :key="page" class="px-3 py-1 rounded border" :class="currentPage === page ? 'bg-blue-600 text-white' : ''" @click="goToPage(page)">{{ page }}</button>
             <button class="p-1.5 border rounded" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)"><ChevronRight class="w-4 h-4"/></button>
          </div>
      </div>
    </div>

    <div v-if="selectedOpp" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="closeDetails">
      <div 
        class="w-full max-w-2xl rounded-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200 flex flex-col max-h-[90vh]"
        :class="isDark ? 'bg-[#161b22] border border-[#30363d]' : 'bg-white border border-[#d0d7de]'"
      >
        <div class="px-6 py-4 border-b flex items-center justify-between flex-shrink-0" :class="isDark ? 'border-[#30363d] bg-[#0d1117]' : 'border-[#d0d7de] bg-[#f6f8fa]'">
          <div class="flex items-center gap-3">
             <div class="bg-green-500/20 p-2 rounded-full"><DollarSign class="w-6 h-6 text-green-500" /></div>
             <div>
               <h3 class="text-lg font-bold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">Opportunity Details</h3>
               <p class="text-xs text-gray-500 flex items-center gap-2">ID: <span class="font-mono text-blue-500">#{{ selectedOpp.id }}</span><span class="w-1 h-1 bg-gray-500 rounded-full"></span>Batch: #{{ selectedOpp.batch_id }}</p>
             </div>
          </div>
          <button @click="closeDetails" class="p-2 rounded hover:bg-gray-500/20"><X class="w-5 h-5" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'" /></button>
        </div>

        <div class="p-6 space-y-6 overflow-y-auto flex-1">
          <div class="grid grid-cols-2 gap-4">
             <div class="p-4 rounded-lg border text-center" :class="isDark ? 'bg-[#0d1117] border-[#30363d]' : 'bg-gray-50 border-gray-200'">
                <div class="text-sm text-gray-500 mb-1">Net Profit</div>
                <div class="text-2xl font-bold text-[#3fb950]">{{ formatCurrency(selectedOpp.profit_usdt) }}</div>
             </div>
             <div class="p-4 rounded-lg border text-center" :class="isDark ? 'bg-[#0d1117] border-[#30363d]' : 'bg-gray-50 border-gray-200'">
                <div class="text-sm text-gray-500 mb-1">ROI (Return)</div>
                <div class="text-2xl font-bold text-[#a371f7]">{{ calculateRoi(selectedOpp) }}%</div>
             </div>
          </div>

          <div class="relative">
             <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-gray-500/10 p-2 rounded-full"><ArrowRightLeft class="w-5 h-5 text-gray-400" /></div>
             <div class="grid grid-cols-2 gap-8">
                <div class="space-y-2">
                  <h4 class="text-xs font-semibold uppercase tracking-wider text-blue-500 border-b border-blue-500/30 pb-1">Buy Side</h4>
                  <div class="flex justify-between text-sm"><span class="text-gray-500">Platform</span><span class="font-medium" :class="textColor">{{ selectedOpp.buy_platform }}</span></div>
                  <div class="flex justify-between text-sm"><span class="text-gray-500">Price</span><span class="font-mono" :class="textColor">{{ formatCurrency(selectedOpp.buy_price) }}</span></div>
                </div>
                <div class="space-y-2 text-right">
                  <h4 class="text-xs font-semibold uppercase tracking-wider text-orange-500 border-b border-orange-500/30 pb-1">Sell Side</h4>
                   <div class="flex justify-between text-sm"><span class="font-medium" :class="textColor">{{ selectedOpp.sell_platform }}</span><span class="text-gray-500">Platform</span></div>
                  <div class="flex justify-between text-sm"><span class="font-mono" :class="textColor">{{ formatCurrency(selectedOpp.sell_price) }}</span><span class="text-gray-500">Price</span></div>
                </div>
             </div>
          </div>

          <div class="space-y-3">
             <h4 class="text-sm font-semibold flex items-center gap-2" :class="textColor"><Clock class="w-4 h-4" /> Timing & Technicals</h4>
             <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm rounded-md border p-3" :class="isDark ? 'bg-[#0d1117] border-[#30363d]' : 'bg-gray-50 border-gray-200'">
                <div class="flex flex-col"><span class="text-xs text-gray-500">Created At</span><span :class="textColor">{{ formatFullTime(getTimeFromItem(selectedOpp)) }}</span></div>
                 <div class="flex flex-col"><span class="text-xs text-gray-500">Block Time</span><span :class="textColor">{{ selectedOpp.details?.block_time ? formatFullTime(selectedOpp.details.block_time) : '--' }}</span></div>
             </div>
          </div>

          <div class="space-y-3 pt-2 border-t" :class="isDark ? 'border-[#30363d]' : 'border-gray-200'">
             <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <h4 class="text-sm font-semibold flex items-center gap-2" :class="textColor"><LineChart class="w-4 h-4" /> Market Context</h4>
                  <div v-if="modalChartLoading" class="flex items-center gap-1 text-xs text-blue-500"><Loader2 class="w-3 h-3 animate-spin"/> Loading...</div>
                </div>
                <button 
                  @click="toggleTimestamp" 
                  class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-xs flex items-center gap-1 transition-colors text-gray-500 hover:text-blue-500"
                  title="Toggle Timestamp"
                >
                  <Binary class="w-3 h-3" /> {{ showTimestamp ? 'Raw' : 'Date' }}
                </button>
             </div>
             <div class="rounded-md border p-2 h-[250px] relative" :class="isDark ? 'bg-[#0d1117] border-[#30363d]' : 'bg-gray-50 border-gray-200'">
                <div ref="modalChartRef" class="w-full h-full"></div>
             </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t flex justify-end flex-shrink-0" :class="isDark ? 'border-[#30363d] bg-[#0d1117]' : 'border-[#d0d7de] bg-[#f6f8fa]'">
           <button @click="closeDetails" class="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded transition-colors">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>