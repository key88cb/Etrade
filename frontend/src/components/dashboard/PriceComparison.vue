<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';
import { Calendar, Loader2, AlertCircle, BarChart3 } from 'lucide-vue-next';
import api from '../../api';

type Theme = 'light' | 'dark';
type LoadingState = 'idle' | 'loading' | 'success' | 'error';
type PricePoint = [number, number];

interface Props {
  theme: Theme;
}

interface PriceSeries {
  uniswap: PricePoint[];
  binance: PricePoint[];
}

const props = defineProps<Props>();

const chartRef = ref<HTMLDivElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

const startDateTime = ref('2025-09-01T00:00');
const endDateTime = ref('2025-09-07T23:59');
const loadingState = ref<LoadingState>('idle');
const errorMessage = ref('');
const seriesData = ref<PriceSeries>({ uniswap: [], binance: [] });

const isDark = computed(() => props.theme === 'dark');
const totalPoints = computed(
  () => seriesData.value.uniswap.length + seriesData.value.binance.length,
);
const hasData = computed(() => totalPoints.value > 0);

const disposeChart = () => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
};

const renderChart = () => {
  if (!chartRef.value) {
    return;
  }

  if (!seriesData.value.uniswap.length && !seriesData.value.binance.length) {
    disposeChart();
    return;
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }

  const textColor = isDark.value ? '#e6edf3' : '#24292f';
  const secondaryTextColor = isDark.value ? '#7d8590' : '#57606a';
  const backgroundColor = isDark.value ? '#161b22' : 'white';
  const borderColor = isDark.value ? '#30363d' : '#d0d7de';
  const gridColor = isDark.value ? '#21262d' : '#eaeef2';

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    title: {
      text: 'USDT/ETH Price Comparison',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: textColor,
      },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor,
      borderColor,
      borderWidth: 1,
      textStyle: {
        color: textColor,
      },
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: borderColor,
        },
      },
      formatter: (params: any) => {
        const date = new Date(params[0].value[0]).toLocaleString('en-US');
        let result = `<div style="font-size: 12px;">`;
        result += `<div style="color: ${secondaryTextColor}; margin-bottom: 4px;">${date}</div>`;
        params.forEach((param: any) => {
          const color = param.seriesName === 'Uniswap V3' ? '#58a6ff' : '#f78166';
          result += `<div style="color: ${color}; margin: 2px 0;">`;
          result += `${param.marker} ${param.seriesName}: $${Number(param.value[1]).toFixed(2)}`;
          result += `</div>`;
        });
        result += `</div>`;
        return result;
      },
    },
    legend: {
      data: ['Uniswap V3', 'Binance'],
      top: 40,
      textStyle: {
        color: secondaryTextColor,
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: 90,
      containLabel: true,
    },
    toolbox: {
      feature: {
        dataZoom: {
          yAxisIndex: 'none',
        },
        restore: {},
        saveAsImage: {},
      },
      iconStyle: {
        borderColor: secondaryTextColor,
      },
      emphasis: {
        iconStyle: {
          borderColor: '#58a6ff',
        },
      },
      right: 20,
      top: 40,
    },
    xAxis: {
      type: 'time',
      axisLine: {
        lineStyle: {
          color: borderColor,
        },
      },
      axisLabel: {
        color: secondaryTextColor,
        fontSize: 11,
        formatter: (value: number) => {
          const date = new Date(value);
          return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(
            date.getMinutes(),
          ).padStart(2, '0')}`;
        },
      },
      splitLine: {
        lineStyle: {
          color: gridColor,
        },
      },
    },
    yAxis: {
      type: 'value',
      name: 'Price (USDT)',
      nameTextStyle: {
        color: secondaryTextColor,
        fontSize: 11,
      },
      axisLine: {
        lineStyle: {
          color: borderColor,
        },
      },
      axisLabel: {
        color: secondaryTextColor,
        fontSize: 11,
        formatter: '${value}',
      },
      splitLine: {
        lineStyle: {
          color: gridColor,
        },
      },
      scale: true,
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
      },
      {
        start: 0,
        end: 100,
        backgroundColor: isDark.value ? '#0d1117' : '#f6f8fa',
        fillerColor: 'rgba(88, 166, 255, 0.1)',
        borderColor,
        handleStyle: {
          color: '#58a6ff',
          borderColor: '#58a6ff',
        },
        textStyle: {
          color: secondaryTextColor,
        },
        dataBackground: {
          lineStyle: {
            color: borderColor,
          },
          areaStyle: {
            color: gridColor,
          },
        },
      },
    ],
    series: [
      {
        name: 'Uniswap V3',
        type: 'line',
        smooth: true,
        symbol: 'none',
        sampling: 'lttb',
        lineStyle: {
          width: 2,
          color: '#58a6ff',
        },
        itemStyle: {
          color: '#58a6ff',
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {
              offset: 0,
              color: 'rgba(88, 166, 255, 0.3)',
            },
            {
              offset: 1,
              color: 'rgba(88, 166, 255, 0.05)',
            },
          ]),
        },
        data: seriesData.value.uniswap,
      },
      {
        name: 'Binance',
        type: 'line',
        smooth: true,
        symbol: 'none',
        sampling: 'lttb',
        lineStyle: {
          width: 2,
          color: '#f78166',
        },
        itemStyle: {
          color: '#f78166',
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {
              offset: 0,
              color: 'rgba(247, 129, 102, 0.3)',
            },
            {
              offset: 1,
              color: 'rgba(247, 129, 102, 0.05)',
            },
          ]),
        },
        data: seriesData.value.binance,
      },
    ],
  };

  chartInstance.setOption(option);
};

watch(
  [() => seriesData.value.uniswap, () => seriesData.value.binance, () => props.theme],
  () => {
    nextTick(() => renderChart());
  },
);

watch(
  () => chartRef.value,
  (element) => {
    if (element && hasData.value) {
      nextTick(() => renderChart());
    }
  },
);

onBeforeUnmount(() => disposeChart());

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
      const timestamp = Number(item[0]);
      const price = Number(item[1]);
      if (Number.isNaN(timestamp) || Number.isNaN(price)) return null;
      return [timestamp, price] as PricePoint;
    })
    .filter((item): item is PricePoint => Array.isArray(item));
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

  try {
    const { data } = await api.getPriceComparisonData({
      startTime: start,
      endTime: end,
    });
    const payload = data?.data ?? {};
    seriesData.value = {
      uniswap: normalizeSeries(payload.uniswap),
      binance: normalizeSeries(payload.binance),
    };
    loadingState.value = 'success';
    await nextTick();
    renderChart();
  } catch (error: any) {
    console.error(error);
    seriesData.value = { uniswap: [], binance: [] };
    loadingState.value = 'error';
    errorMessage.value =
      error?.message ?? error?.data?.message ?? '价格数据加载失败';
  }
};
</script>

<template>
  <div class="space-y-4">
    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex flex-wrap items-end gap-3">
        <div class="flex-1 min-w-[200px]">
          <label
            class="block text-xs mb-1.5"
            :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
          >
            Start Date
          </label>
          <div class="relative">
            <Calendar
              class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
              :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
            />
            <input
              type="datetime-local"
              v-model="startDateTime"
              class="w-full pl-9 pr-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
          </div>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label
            class="block text-xs mb-1.5"
            :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
          >
            End Date
          </label>
          <div class="relative">
            <Calendar
              class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
              :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
            />
            <input
              type="datetime-local"
              v-model="endDateTime"
              class="w-full pl-9 pr-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm focus:border-transparent"
              :class="isDark
                ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'"
            />
          </div>
        </div>

        <button
          type="button"
          :disabled="loadingState === 'loading'"
          class="px-4 py-1.5 bg-[#238636] text-white rounded-md text-sm hover:bg-[#2ea043] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
      <div class="relative h-[500px]">
        <div
          ref="chartRef"
          class="h-full w-full"
          v-show="loadingState === 'success' && hasData"
        />

        <div
          v-if="loadingState === 'idle'"
          class="absolute inset-0 flex items-center justify-center"
          :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'"
        >
          <div class="text-center">
            <BarChart3 class="w-16 h-16 mx-auto mb-3 opacity-50" />
            <p class="text-sm">Select date range and click "Load Data"</p>
            <p class="text-xs mt-1" :class="isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'">
              to view price chart
            </p>
          </div>
        </div>

        <div
          v-else-if="loadingState === 'loading'"
          class="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm"
        >
          <div class="text-center">
            <Loader2 class="w-12 h-12 text-[#58a6ff] animate-spin mx-auto mb-3" />
            <p class="text-[#58a6ff] text-sm">Loading data...</p>
          </div>
        </div>

        <div
          v-else-if="loadingState === 'error'"
          class="absolute inset-0 flex items-center justify-center"
        >
          <div class="text-center">
            <AlertCircle class="w-12 h-12 text-[#f85149] mx-auto mb-3" />
            <p class="text-[#f85149] text-sm">
              {{ errorMessage || 'Failed to load data' }}
            </p>
            <p class="text-xs mt-1" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              Please try again
            </p>
          </div>
        </div>

        <div
          v-else-if="loadingState === 'success' && !hasData"
          class="absolute inset-0 flex items-center justify-center"
        >
          <div class="text-center">
            <AlertCircle class="w-12 h-12 text-[#d29922] mx-auto mb-3" />
            <p class="text-[#d29922] text-sm">No data available</p>
            <p class="text-xs mt-1" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
              for selected time range
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="loadingState === 'success' && hasData"
      class="border rounded-md p-3"
      :class="
        isDark ? 'bg-[#388bfd26] border-[#1f6feb] text-[#e6edf3]' : 'bg-[#ddf4ff] border-[#54aeff] text-[#0969da]'
      "
    >
      <div class="flex items-start gap-2">
        <div class="text-[#58a6ff] mt-0.5">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
            <path
              d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"
            />
          </svg>
        </div>
        <div class="flex-1 text-sm">
          Use mouse wheel or toolbar to zoom chart. Loaded
          <span class="text-[#58a6ff]">{{ totalPoints }}</span>
          data points.
        </div>
      </div>
    </div>
  </div>
</template>
