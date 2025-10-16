// 在你的 Vue 组件文件，例如 ChartComponent.vue

<template>
  <div ref="chartRef" style="width: 600px; height: 400px;"></div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts/core';
// 1. 引入所需的图表类型，例如：柱状图（BarChart）
import { BarChart } from 'echarts/charts';
// 2. 引入所需的组件，例如：标题组件（TitleComponent）、提示框组件（TooltipComponent）、直角坐标系（GridComponent）
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components';
// 3. 引入 Canvas 渲染器
import { CanvasRenderer } from 'echarts/renderers';

import { ref, onMounted, onBeforeUnmount } from 'vue';
import type { EChartsType } from 'echarts/core'; // 导入类型支持

// 注册必须的组件
echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  BarChart,
  CanvasRenderer
]);

const chartRef = ref<HTMLElement | null>(null);
let myChart: EChartsType | null = null;

onMounted(() => {
  if (chartRef.value) {
    // 基于准备好的dom，初始化echarts实例
    myChart = echarts.init(chartRef.value);

    // 绘制图表
    const option = {
      title: {
        text: 'ECharts 示例'
      },
      tooltip: {},
      xAxis: {
        data: ['衬衫', '羊毛衫', '雪纺衫', '裤子', '高跟鞋', '袜子']
      },
      yAxis: {},
      series: [
        {
          name: '销量',
          type: 'bar',
          data: [5, 20, 36, 10, 10, 20]
        }
      ]
    };
    
    myChart.setOption(option);
  }
});

onBeforeUnmount(() => {
  // 在组件销毁前，销毁图表实例，释放内存
  if (myChart) {
    myChart.dispose();
  }
});
</script>