<template>
  <div class="page-container">
    <a-card class="main-card" :bordered="false">
      <template #title>
        <div class="card-header">
          <DollarOutlined class="header-icon" />
          <span class="header-title">套利机会识别系统</span>
          <a-tag color="blue" class="mvp-tag">实时数据</a-tag>
        </div>
      </template>
      <template #extra>
        <a-button 
          type="primary" 
          :loading="loading" 
          @click="fetchOpportunities"
          class="refresh-button"
        >
          <ReloadOutlined v-if="!loading" />
          {{ loading ? '加载中...' : '刷新套利机会' }}
        </a-button>
      </template>

      <a-alert
        v-if="error"
        :message="error"
        type="error"
        closable
        @close="error = null"
        class="error-alert"
      />

      <div v-else-if="loading" class="loading-container">
        <a-spin size="large">
          <template #tip>
            <div class="loading-text">正在从后端加载实时数据...</div>
          </template>
        </a-spin>
      </div>

      <div v-else>
        <a-row :gutter="16" class="stats-row">
          <a-col :xs="24" :sm="8">
            <a-card :bordered="false" class="stat-card stat-total">
              <a-statistic
                title="总机会数"
                :value="opportunities.length"
                :value-style="{ color: '#1890ff' }"
              >
                <template #prefix>
                  <DatabaseOutlined />
                </template>
              </a-statistic>
            </a-card>
          </a-col>
          <a-col :xs="24" :sm="8">
            <a-card :bordered="false" class="stat-card stat-max">
              <a-statistic
                title="最大利润"
                :value="maxProfit"
                :precision="4"
                suffix="USDT"
                :value-style="{ color: '#52c41a' }"
              >
                <template #prefix>
                  <TrophyOutlined />
                </template>
              </a-statistic>
            </a-card>
          </a-col>
          <a-col :xs="24" :sm="8">
            <a-card :bordered="false" class="stat-card stat-avg">
              <a-statistic
                title="平均利润"
                :value="avgProfit"
                :precision="4"
                suffix="USDT"
                :value-style="{ color: '#faad14' }"
              >
                <template #prefix>
                  <LineChartOutlined />
                </template>
              </a-statistic>
            </a-card>
          </a-col>
        </a-row>
        
        <a-table
          :columns="columns"
          :data-source="opportunities"
          :pagination="{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number) => `共 ${total} 条记录`,
          }"
          :row-key="(record: Opportunity) => record.id"
          :locale="{
            emptyText: '暂无套利机会数据',
          }"
          class="opportunities-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'id'">
              <a-tag color="processing">{{ record.id }}</a-tag>
            </template>
            
            <template v-else-if="column.key === 'buy_platform'">
              <a-tag color="#2db7f5">
                <ArrowUpOutlined />
                {{ record.buy_platform }}
              </a-tag>
            </template>
            
            <template v-else-if="column.key === 'sell_platform'">
              <a-tag color="#f50">
                <ArrowDownOutlined />
                {{ record.sell_platform }}
              </a-tag>
            </template>
            
            <template v-else-if="column.key === 'buy_price'">
              <span class="price-text buy-price-text">${{ record.buy_price.toFixed(4) }}</span>
            </template>
            
            <template v-else-if="column.key === 'sell_price'">
              <span class="price-text sell-price-text">${{ record.sell_price.toFixed(4) }}</span>
            </template>
            
            <template v-else-if="column.key === 'profit_usdt'">
              <a-statistic
                :value="record.profit_usdt"
                :precision="4"
                suffix="USDT"
                :value-style="{ color: '#3f8600', fontSize: '14px', fontWeight: 'bold' }"
              >
                <template #prefix>
                  <RiseOutlined />
                </template>
              </a-statistic>
            </template>
          </template>
        </a-table>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import api from '../api'; // 假设您的 api 路径是正确的
import {
  DollarOutlined,
  ReloadOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RiseOutlined,
  DatabaseOutlined,
  TrophyOutlined,
  LineChartOutlined
} from '@ant-design/icons-vue';

interface Opportunity {
  id: number;
  buy_platform: string;
  sell_platform: string;
  buy_price: number;
  sell_price: number;
  profit_usdt: number;
}

const columns = [
  {
    title: 'ID',
    dataIndex: 'id',
    key: 'id',
    width: 80,
    align: 'center' as const,
  },
  {
    title: '买入平台',
    dataIndex: 'buy_platform',
    key: 'buy_platform',
    align: 'center' as const,
    responsive: ['sm'] as const,
  },
  {
    title: '卖出平台',
    dataIndex: 'sell_platform',
    key: 'sell_platform',
    align: 'center' as const,
    responsive: ['sm'] as const,
  },
  {
    title: '买入价格 ($)',
    dataIndex: 'buy_price',
    key: 'buy_price',
    align: 'right' as const,
    sorter: (a: Opportunity, b: Opportunity) => a.buy_price - b.buy_price,
  },
  {
    title: '卖出价格 ($)',
    dataIndex: 'sell_price',
    key: 'sell_price',
    align: 'right' as const,
    sorter: (a: Opportunity, b: Opportunity) => a.sell_price - b.sell_price,
  },
  {
    title: '预计利润 (USDT)',
    dataIndex: 'profit_usdt',
    key: 'profit_usdt',
    align: 'right' as const,
    sorter: (a: Opportunity, b: Opportunity) => a.profit_usdt - b.profit_usdt,
    defaultSortOrder: 'descend' as const,
  },
];

const opportunities = ref<Opportunity[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const maxProfit = computed(() => {
  if (opportunities.value.length === 0) return 0;
  return Math.max(...opportunities.value.map(opp => opp.profit_usdt));
});

const avgProfit = computed(() => {
  if (opportunities.value.length === 0) return 0;
  const sum = opportunities.value.reduce((acc, opp) => acc + opp.profit_usdt, 0);
  return sum / opportunities.value.length;
});

const fetchOpportunities = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const response = await api.getOpportunities();
    
    if (response.data && response.data.code === 200) {
      opportunities.value = response.data.data || [];
    } else {
      error.value = response.data?.message || '获取数据失败，请检查数据格式';
      opportunities.value = [];
    }
  } catch (err: any) {
    console.error('获取套利机会失败:', err);
    error.value = err.message || '网络请求失败，请检查后端服务是否可用';
    opportunities.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchOpportunities();
});
</script>

<style scoped>
.page-container {
  padding: 24px;
  background-color: #f0f2f5; /* 略微灰白背景 */
  min-height: 100vh;
}

.main-card {
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); /* 略微提升阴影 */
  border-radius: 12px;
}

/* 头部样式 */
.card-header {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: #1890ff; /* 蓝色标题 */
}

.header-icon {
  font-size: 24px;
  margin-right: 8px;
  color: #1890ff;
}

.header-title {
  margin-right: 10px;
}

.mvp-tag {
  font-size: 12px;
  height: 20px;
  line-height: 18px;
}

/* 刷新按钮 */
.refresh-button {
  background-color: #1890ff;
  border-color: #1890ff;
}
.refresh-button:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background-color: #e6f7ff; /* 浅蓝色背景 */
  border-left: 5px solid #1890ff; /* 蓝色强调边框 */
  border-radius: 8px;
  transition: all 0.3s;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
  transform: translateY(-2px);
}

/* 价格和利润文本 */
.price-text {
  font-family: 'Consolas', 'Courier New', monospace;
  font-weight: 600;
  font-size: 14px;
}

.buy-price-text {
  color: #1890ff; /* 蓝色 */
}

.sell-price-text {
  color: #f5222d; /* 红色 */
}

/* 表格样式 */
.opportunities-table :deep(.ant-table-thead > tr > th) {
  background-color: #e6f7ff; /* 浅蓝色表头 */
  color: #0050b3; /* 深蓝色文字 */
  font-weight: 700;
}

.opportunities-table :deep(.ant-table-row:hover) {
  background-color: #f0f8ff !important; /* 鼠标悬停时的浅蓝色 */
}

/* 加载和错误提示 */
.loading-container {
  text-align: center;
  padding: 50px 0;
}

.loading-text {
  margin-top: 10px;
  color: #1890ff;
}

.error-alert {
  margin-bottom: 24px;
}
</style>