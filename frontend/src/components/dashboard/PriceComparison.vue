<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount, onMounted } from 'vue';
import * as echarts from 'echarts';
import { Calendar, Loader2, AlertCircle, LineChart } from 'lucide-vue-next';
import api from '../../api';

// --- 类型定义 ---
type Theme = 'light' | 'dark';
type LoadingState = 'idle' | 'loading' | 'success' | 'error';
type PricePoint = [number, number];

interface Props {
  theme: Theme;
  taskId?: string | number;
}

interface PriceSeries {
  uniswap: PricePoint[];
  binance: PricePoint[];
}

const props = defineProps<Props>();

// --- DOM Refs ---
const priceChartRef = ref<HTMLDivElement | null>(null);
let priceChartInstance: echarts.ECharts | null = null;

// --- State ---
const startDateTime = ref('2025-09-01T00:00');
const endDateTime = ref('2025-09-07T23:59');
const loadingState = ref<LoadingState>('idle');
const errorMessage = ref('');

// 数据源
const seriesData = ref<PriceSeries>({ uniswap: [], binance: [] });

// --- Computed ---
const isDark = computed(() => props.theme === 'dark');
const totalPoints = computed(() => seriesData.value.uniswap.length + seriesData.value.binance.length);
const hasPriceData = computed(() => totalPoints.value > 0);

// 通用样式变量
const textColor = computed(() => isDark.value ? '#e6edf3' : '#24292f');
const secondaryTextColor = computed(() => isDark.value ? '#7d8590' : '#57606a');
const backgroundColor = computed(() => isDark.value ? '#161b22' : 'white');
const borderColor = computed(() => isDark.value ? '#30363d' : '#d0d7de');

// ==========================================
// 渲染主图表: 价格对比
// ==========================================
const renderPriceChart = () => {
  if (!priceChartRef.value) return;
  // 如果没有数据，也要尝试初始化以便显示空状态或清除旧图表
  if (!seriesData.value.uniswap.length && !seriesData.value.binance.length) {
    priceChartInstance?.dispose();
    priceChartInstance = null;
    return;
  }

  if (!priceChartInstance) priceChartInstance = echarts.init(priceChartRef.value);

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    title: {
      text: 'USDT/ETH Price Comparison',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 16, fontWeight: 600, color: textColor.value },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: backgroundColor.value,
      borderColor: borderColor.value,
      textStyle: { color: textColor.value },
      axisPointer: { type: 'cross', lineStyle: { color: borderColor.value } },
      formatter: (params: any) => {
        const date = new Date(params[0].value[0]).toLocaleString('en-US');
        let result = `<div style="font-size: 12px;"><div style="color: ${secondaryTextColor.value}; margin-bottom: 4px;">${date}</div>`;
        params.forEach((param: any) => {
          const color = param.seriesName === 'Uniswap V3' ? '#58a6ff' : '#f78166';
          result += `<div style="color: ${color}; margin: 2px 0;">${param.marker} ${param.seriesName}: $${Number(param.value[1]).toFixed(2)}</div>`;
        });
        return result + `</div>`;
      },
    },
    legend: {
      data: ['Uniswap V3', 'Binance'],
      top: 40,
      textStyle: { color: secondaryTextColor.value },
    },
    grid: { left: '3%', right: '4%', bottom: '12%', top: 90, containLabel: true },
    toolbox: {
      feature: { dataZoom: { yAxisIndex: 'none' }, restore: {}, saveAsImage: {} },
      iconStyle: { borderColor: secondaryTextColor.value },
      right: 20, top: 40,
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: borderColor.value } },
      axisLabel: { color: secondaryTextColor.value, fontSize: 11 },
      splitLine: { lineStyle: { color: isDark.value ? '#21262d' : '#eaeef2' } },
    },
    yAxis: {
      type: 'value',
      name: 'Price (USDT)',
      nameTextStyle: { color: secondaryTextColor.value },
      axisLine: { lineStyle: { color: borderColor.value } },
      axisLabel: { color: secondaryTextColor.value },
      splitLine: { lineStyle: { color: isDark.value ? '#21262d' : '#eaeef2' } },
      scale: true,
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        start: 0, end: 100,
        borderColor: borderColor.value,
        textStyle: { color: secondaryTextColor.value },
        dataBackground: { lineStyle: { color: borderColor.value }, areaStyle: { color: isDark.value ? '#21262d' : '#eaeef2' } },
      },
    ],
    series: [
      {
        name: 'Uniswap V3',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#58a6ff' },
        itemStyle: { color: '#58a6ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(88, 166, 255, 0.3)' },
            { offset: 1, color: 'rgba(88, 166, 255, 0.05)' },
          ]),
        },
        data: seriesData.value.uniswap,
      },
      {
        name: 'Binance',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#f78166' },
        itemStyle: { color: '#f78166' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(247, 129, 102, 0.3)' },
            { offset: 1, color: 'rgba(247, 129, 102, 0.05)' },
          ]),
        },
        data: seriesData.value.binance,
      },
    ],
  };

  priceChartInstance.setOption(option);
};

// --- 生命周期与监听 ---
watch([() => seriesData.value, () => props.theme], () => {
  nextTick(() => renderPriceChart());
});

watch(() => priceChartRef.value, (el) => {
  if (el && hasPriceData.value) nextTick(() => renderPriceChart());
});

const handleResize = () => priceChartInstance?.resize();

onMounted(() => {
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  priceChartInstance?.dispose();
});

// --- 数据处理 ---
const buildTimestampRange = () => {
  const start = new Date(startDateTime.value).getTime();
  const end = new Date(endDateTime.value).getTime();
  return { start, end };
};

const normalizeSeries = (values?: unknown): PricePoint[] => {
  if (!Array.isArray(values)) return [];
  return values
    .map((item) => {
      if (!Array.isArray(item) || item.length < 2) return null;
      return [Number(item[0]), Number(item[1])] as PricePoint;
    })
    .filter((item): item is PricePoint => item !== null);
};

const handleLoad = async () => {
  const { start, end } = buildTimestampRange();
  if (Number.isNaN(start) || Number.isNaN(end) || start >= end) {
    errorMessage.value = '请选择正确的时间范围';
    loadingState.value = 'error';
    return;
  }

  loadingState.value = 'loading';
  errorMessage.value = '';
  seriesData.value = { uniswap: [], binance: [] };

  try {
    // 仅获取价格数据
    const { data } = await api.getPriceComparisonData({ 
        startTime: start, 
        endTime: end, 
        taskId: props.taskId 
    });
    
    const payload = data?.data ?? {};
    seriesData.value = {
      uniswap: normalizeSeries(payload.uniswap),
      binance: normalizeSeries(payload.binance),
    };

    loadingState.value = 'success';
    await nextTick();
    renderPriceChart();

  } catch (error: any) {
    console.error(error);
    loadingState.value = 'error';
    errorMessage.value = error?.message ?? '数据加载失败';
  }
};

// 自动加载 TaskID
watch(() => props.taskId, (newId) => { if (newId) handleLoad(); }, { immediate: true });
</script>

<template>
  <div class="space-y-6">
    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex flex-wrap items-end gap-3">
        <div class="flex-1 min-w-[200px]">
          <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">Start Date</label>
          <div class="relative">
            <Calendar class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none opacity-50" />
            <input
              type="datetime-local"
              v-model="startDateTime"
              class="w-full pl-9 pr-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]' : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
          </div>
        </div>
        <div class="flex-1 min-w-[200px]">
          <label class="block text-xs mb-1.5" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">End Date</label>
          <div class="relative">
            <Calendar class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none opacity-50" />
            <input
              type="datetime-local"
              v-model="endDateTime"
              class="w-full pl-9 pr-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]' : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
          </div>
        </div>
        <button
          type="button"
          :disabled="loadingState === 'loading'"
          class="px-4 py-1.5 bg-[#238636] text-white rounded-md text-sm hover:bg-[#2ea043] transition-colors disabled:opacity-50 flex items-center gap-2"
          @click="handleLoad"
        >
          <Loader2 v-if="loadingState === 'loading'" class="w-4 h-4 animate-spin" />
          {{ loadingState === 'loading' ? 'Loading...' : 'Load Data' }}
        </button>
      </div>
    </div>

    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="relative h-[450px]">
        <div ref="priceChartRef" class="h-full w-full" v-show="loadingState === 'success' && hasPriceData" />

        <div v-if="loadingState === 'idle'" class="absolute inset-0 flex items-center justify-center opacity-60">
          <div class="text-center">
            <LineChart class="w-16 h-16 mx-auto mb-3" />
            <p class="text-sm">Click "Load Data" to view analysis</p>
          </div>
        </div>
        <div v-else-if="loadingState === 'loading'" class="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm">
           <Loader2 class="w-10 h-10 text-[#58a6ff] animate-spin" />
        </div>
        <div v-else-if="loadingState === 'error'" class="absolute inset-0 flex items-center justify-center text-[#f85149]">
           <div class="text-center"><AlertCircle class="w-12 h-12 mx-auto mb-2" /><p>{{ errorMessage }}</p></div>
        </div>
        <div v-else-if="loadingState === 'success' && !hasPriceData" class="absolute inset-0 flex items-center justify-center text-[#d29922]">
           <p>No price data available for this range.</p>
        </div>
      </div>
    </div>
    
    <div v-if="loadingState === 'success' && hasPriceData" class="border rounded-md p-3 text-sm"
         :class="isDark ? 'bg-[#388bfd26] border-[#1f6feb] text-[#e6edf3]' : 'bg-[#ddf4ff] border-[#54aeff] text-[#0969da]'">
        Loaded {{ totalPoints }} price points.
    </div>
  </div>
</template>