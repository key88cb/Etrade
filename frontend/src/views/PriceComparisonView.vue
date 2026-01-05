<template>
  <div class="page-container">
    <a-card class="main-card" :bordered="false">
      <template #title>
        <div class="card-header">
          <LineChartOutlined class="header-icon" />
          <span class="header-title">价格可视化对比</span>
          <a-tag color="purple" class="mvp-tag">Uniswap vs. Binance</a-tag>
        </div>
      </template>

      <a-space direction="vertical" size="middle" style="display: flex; margin-bottom: 20px;">
        <a-range-picker
          v-model:value="selectedDateRange"
          :allowClear="false"
          style="width: 300px;"
          format="YYYY-MM-DD"  
        />
        <a-button
          type="primary"
          @click="fetchChartData"
          :loading="loading"
          :disabled="!selectedDateRange || selectedDateRange.length !== 2"
        >
          <SearchOutlined v-if="!loading" />
          {{ loading ? '正在加载...' : '加载图表数据' }}
        </a-button>
      </a-space>

      <div v-if="loading" class="loading-container">
        <a-spin size="large">
          <template #tip>
            <div class="loading-text">正在加载聚合价格数据...</div>
          </template>
        </a-spin>
      </div>

      <a-alert
        v-if="error"
        :message="error"
        type="error"
        show-icon
        closable
        @close="error = null"
        class="error-alert"
      />

      <div v-show="!loading && !error && chartOption" ref="chartRef" class="chart-container"></div>

      <a-empty v-if="!loading && !error && !chartOption" description="请选择日期范围并点击加载按钮" />

    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted } from 'vue';
import api from '../api'; // 确保这个路径指向你导出的api实例
import * as echarts from 'echarts/core';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';

// 1. 引入图表类型：折线图
import { LineChart } from 'echarts/charts';
// 2. 引入组件：标题、提示、坐标系、图例、数据缩放
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent
} from 'echarts/components';
// 3. 引入 Canvas 渲染器
import { CanvasRenderer } from 'echarts/renderers';

// 4. 引入 Ant Design 图标
import { LineChartOutlined, SearchOutlined } from '@ant-design/icons-vue';

// 5. 引入 Dayjs 及类型
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import utc from 'dayjs/plugin/utc'; // 引入 UTC 插件以确保时间正确
dayjs.extend(utc); // 使用 UTC 插件

// 注册必须的 ECharts 组件
echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  LineChart,
  CanvasRenderer
]);

// --- 响应式状态 ---
const chartRef = ref<HTMLElement | null>(null);
let myChart: EChartsType | null = null;
const loading = ref(false); // 初始时不加载
const error = ref<string | null>(null);
const chartOption = ref<EChartsCoreOption | null>(null); // 用于存储图表配置

// --- 日期范围选择 ---
// 预设：2025-09-01 ~ 2025-09-30（UTC）
const presetStartDate = dayjs.utc('2025-09-01');
const presetEndDate = dayjs.utc('2025-09-30');
const selectedDateRange = ref<[Dayjs, Dayjs]>([presetStartDate, presetEndDate]);

// --- 后端返回的数据结构 ---
interface PriceData {
  uniswap: [number, number][]; // [timestamp_ms, price]
  binance: [number, number][];
}

// --- ECharts 配置函数 ---
const getChartOption = (data: PriceData, minRange: number, maxRange: number): EChartsCoreOption => {
  return {
    title: {
      text: `Uniswap vs. Binance 价格对比`,
      subtext: `时间范围: ${dayjs(minRange).utc().format('YYYY-MM-DD')} - ${dayjs(maxRange).utc().format('YYYY-MM-DD')}`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['Uniswap', 'Binance'],
      top: 'bottom', // 图例放在底部
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%', // 为 dataZoom 和 legend 留出空间
      containLabel: true
    },
    xAxis: {
      type: 'time',
      min: minRange,
      max: maxRange,
      axisLabel: {
         formatter: '{yyyy}-{MM}-{dd}' // 格式化X轴标签
      },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: { formatter: '${value}' }
    },
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', bottom: '2%'} // 滑动条放在更底部
    ],
    series: [
      {
        name: 'Uniswap',
        type: 'line',
        showSymbol: false,
        data: data.uniswap
      },
      {
        name: 'Binance',
        type: 'line',
        showSymbol: false,
        data: data.binance
      }
    ]
  };
};

// --- 数据获取与图表初始化 ---
const fetchChartData = async () => {
  if (!selectedDateRange.value || selectedDateRange.value.length !== 2) {
    error.value = "请选择有效的日期范围";
    return;
  }

  loading.value = true;
  error.value = null;
  chartOption.value = null; // 清空旧图表配置，以便显示Loading
  myChart?.clear(); // 清空旧图表画布

  // 获取选定的开始和结束时间 (毫秒 UTC 时间戳)
  const startTimeMs = selectedDateRange.value[0].utc().startOf('day').valueOf();
  const endTimeMs = selectedDateRange.value[1].utc().endOf('day').valueOf();

  try {
    const response = await api.getPriceComparisonData({
      startTime: startTimeMs,
      endTime: endTimeMs,
    });

    // 假设 api 返回格式 { code: 200, data: { ... } } 或直接返回数据
    // 需要根据你的Go后端 utils.Success 返回格式调整
    let apiData: any;
    if (response.data && typeof response.data === 'object' && 'code' in response.data) {
        // 假设是 { code: 200, data: { ... } } 格式
        if ((response.data as any).code === 200) {
            apiData = (response.data as any).data;
        } else {
            throw new Error((response.data as any)?.message || '后端返回错误');
        }
    } else {
        // 假设直接返回数据
        apiData = response.data;
    }

    const chartData: PriceData = apiData;

    if (!chartData || (!chartData.uniswap?.length && !chartData.binance?.length)) {
      error.value = "选定时间范围内没有找到聚合数据";
      return;
    }

    initChart(chartData, startTimeMs, endTimeMs);

  } catch (err: any) {
    console.error('获取价格对比数据失败:', err);
    // 尝试解析更详细的错误信息
    let errorMessage = '网络请求失败或处理数据出错';
    if (err.response && err.response.data && typeof err.response.data === 'object' && 'error' in err.response.data) {
        errorMessage = `后端错误: ${err.response.data.error}`;
    } else if (err.message) {
        errorMessage = err.message;
    }
    error.value = errorMessage;
  } finally {
    loading.value = false;
  }
};

// 初始化图表的函数
const initChart = (data: PriceData, minRange: number, maxRange: number) => {
  if (chartRef.value) {
      // 检查 ECharts 实例是否已存在，不存在则初始化
      if (!myChart) {
          myChart = echarts.init(chartRef.value);
          // 添加窗口大小调整的监听 (只需添加一次)
          window.addEventListener('resize', resizeChart);
      }
      const option = getChartOption(data, minRange, maxRange);
      chartOption.value = option; // 存储配置用于 v-if 判断
      myChart.setOption(option, true); // true表示不合并，重新绘制
  } else {
      console.error("图表DOM元素未准备好");
  }
};


// 图表自适应
const resizeChart = () => {
  myChart?.resize();
};

// --- Vue 生命周期钩子 ---
// 进入页面后自动加载预设范围的数据（仍可手动调整范围后再次点击按钮）
onMounted(() => {
  fetchChartData();
});

onBeforeUnmount(() => {
  // 销毁图表实例和事件监听
  if (myChart) {
    myChart.dispose();
    myChart = null; // 置空引用
  }
  window.removeEventListener('resize', resizeChart);
});
</script>

<style scoped>
:global(:root) {
  --gh-bg: #f6f8fa;
  --gh-surface: #ffffff;
  --gh-border: #d0d7de;
  --gh-muted: #57606a;
  --gh-accent: #0969da;
}

:global(.dark) {
  --gh-bg: #0d1117;
  --gh-surface: #161b22;
  --gh-border: #30363d;
  --gh-muted: #7d8590;
  --gh-accent: #58a6ff;
}

.page-container {
  padding: 0;
  background-color: transparent;
}
.main-card {
  background: var(--gh-surface);
  border: 1px solid var(--gh-border);
  box-shadow: none;
  border-radius: 12px;
}
.card-header {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: var(--gh-accent);
}
.header-icon {
  font-size: 24px;
  margin-right: 8px;
  color: var(--gh-accent);
}
.header-title {
  margin-right: 10px;
}
.mvp-tag {
  font-size: 12px;
  height: 20px;
  line-height: 18px;
}
.chart-container {
  height: 600px;
  width: 100%;
}
.loading-container {
  text-align: center;
  padding: 100px 0;
  min-height: 600px; /* 保持和图表一样高 */
  display: flex;
  justify-content: center;
  align-items: center;
}
.loading-text {
  margin-top: 10px;
  color: var(--gh-accent);
}
.error-alert {
  margin-bottom: 24px;
}
</style>
