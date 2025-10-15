<template>
  <div class="container">
    <header>
      <h1>套利机会识别 (MVP)</h1>
    </header>

    <main>
      <div v-if="loading" class="loading">
        正在从后端加载数据...
      </div>

      <div v-if="error" class="error">
        加载数据失败: {{ error }}
      </div>

      <table v-if="!loading && !error && opportunities.length > 0">
        <thead>
          <tr>
            <th>ID</th>
            <th>买入平台</th>
            <th>卖出平台</th>
            <th>买入价格</th>
            <th>卖出价格</th>
            <th>预计利润 (USDT)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="opp in opportunities" :key="opp.id">
            <td>{{ opp.id }}</td>
            <td>{{ opp.buy_platform }}</td>
            <td>{{ opp.sell_platform }}</td>
            <td>{{ opp.buy_price.toFixed(2) }}</td>
            <td>{{ opp.sell_price.toFixed(2) }}</td>
            <td class="profit">{{ opp.profit_usdt.toFixed(4) }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && !error && opportunities.length === 0" class="no-data">
        在数据库中没有发现套利机会。
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';

// 定义后端API的地址
const API_URL = 'http://localhost:8080/api/v1/opportunities';

// 定义接口返回的数据结构类型
interface Opportunity {
  id: number;
  buy_platform: string;
  sell_platform: string;
  buy_price: number;
  sell_price: number;
  profit_usdt: number;
}

// 创建响应式变量来存储数据、加载和错误状态
const opportunities = ref<Opportunity[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// 定义一个异步函数来获取数据
const fetchData = async () => {
  try {
    const response = await axios.get<Opportunity[]>(API_URL);
    opportunities.value = response.data;
  } catch (err) {
    console.error("Failed to fetch data:", err);
    error.value = (err as Error).message;
  } finally {
    loading.value = false;
  }
};

// onMounted 是一个生命周期钩子，它会在组件挂载到页面后执行
onMounted(() => {
  fetchData();
});
</script>

<style>
/* 添加一些简单的样式让表格更好看 */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f4f7f9;
  color: #333;
  margin: 0;
}

.container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 1rem;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

header h1 {
  text-align: center;
  color: #2c3e50;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 2rem;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

thead th {
  background-color: #eef1f4;
  font-weight: bold;
}

tbody tr:hover {
  background-color: #f6f6f6;
}

.profit {
  color: #28a745;
  font-weight: bold;
}

.loading, .error, .no-data {
  text-align: center;
  margin-top: 2rem;
  font-size: 1.2rem;
  color: #777;
}

.error {
  color: #dc3545;
}
</style>