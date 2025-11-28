<template>
  <div class="page-container">
    <a-card class="main-card" :bordered="false">
      <template #title>
        <div class="card-header">
          <DollarOutlined class="header-icon" />
          <span class="header-title">批次 & 套利机会中心</span>
          <a-tag color="blue" class="mvp-tag">批次驱动</a-tag>
        </div>
      </template>
      <template #extra>
        <a-button 
          type="primary" 
          :loading="loading || batchesLoading"
          @click="handleRefreshAll"
          class="refresh-button"
        >
          <ReloadOutlined v-if="!loading && !batchesLoading" />
          {{ loading || batchesLoading ? '加载中...' : '刷新数据' }}
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

      <a-row :gutter="16">
        <a-col :xs="24" :lg="6">
          <a-card title="批次管理" size="small" class="side-card" :loading="batchesLoading">
            <a-list
              :data-source="batches"
              bordered
              size="small"
              class="batch-list"
              :locale="{ emptyText: '暂无批次，请先在 Data Management 中创建。' }"
            >
              <template #renderItem="{ item }">
                <a-list-item
                  class="batch-item"
                  :class="{ active: isBatchOpened(item.id) }"
                >
                  <div class="batch-info" @click="toggleBatch(item)">
                    <div class="batch-name">
                      {{ item.name }}
                      <a-tag
                        v-if="isBatchOpened(item.id)"
                        color="green"
                        :bordered="false"
                        style="margin-left: 8px"
                      >
                        已打开
                      </a-tag>
                    </div>
                    <div class="batch-meta">ID: {{ item.id }}</div>
                    <div class="batch-meta">刷新：{{ item.last_refreshed_at ?? '尚未刷新' }}</div>
                  </div>
                  <div class="batch-actions">
                    <a-button
                      type="primary"
                      size="small"
                      ghost
                      @click.stop="toggleBatch(item)"
                    >
                      {{ isBatchOpened(item.id) ? '关闭批次' : '打开批次' }}
                    </a-button>
                  </div>
                </a-list-item>
              </template>
            </a-list>
          </a-card>

          <a-card title="快速生成报告" size="small" class="side-card mt-4">
            <a-form layout="vertical" @finish="submitReport">
              <a-form-item label="批次 ID" required>
                <a-input-number
                  v-model:value="reportForm.batch_id"
                  :min="1"
                  style="width: 100%"
                  :placeholder="reportBatchPlaceholder"
                />
              </a-form-item>
              <a-form-item label="模板 ID">
                <a-input-number v-model:value="reportForm.template_id" :min="1" style="width: 100%" />
              </a-form-item>
              <a-form-item label="格式">
                <a-select v-model:value="reportForm.format">
                  <a-select-option value="PDF">PDF</a-select-option>
                  <a-select-option value="HTML">HTML</a-select-option>
                  <a-select-option value="Markdown">Markdown</a-select-option>
                </a-select>
              </a-form-item>
              <a-button type="primary" html-type="submit" block :loading="reportLoading">
                提交报告任务
              </a-button>
            </a-form>
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="18">
          <div class="active-batch-header">
            <div>
              <h3>批次概览</h3>
              <p class="text-sm text-gray-500">
                从左侧打开一个或多个批次，可随时关闭；下面的表格将聚合所有已打开批次的套利机会。
              </p>
            </div>
            <div class="actions">
              <a-button size="small" @click="fetchBatches">刷新批次</a-button>
              <a-button
                size="small"
                type="primary"
                ghost
                :disabled="!reportForm.batch_id"
                @click="reportForm.batch_id && fetchReports(reportForm.batch_id)"
              >
                刷新报告
              </a-button>
            </div>
          </div>

          <div v-if="openedBatches.length" class="opened-tags">
            <a-tag
              v-for="batch in openedBatches"
              :key="batch.id"
              color="blue"
              closable
              @close.prevent.stop="closeBatch(batch.id)"
            >
              {{ batch.name }} (#{{ batch.id }})
            </a-tag>
          </div>
          <div v-else class="text-sm text-gray-500 mb-4">
            暂未选择批次，请在左侧批次列表中点击打开。
          </div>

          <a-row :gutter="16" class="stats-row" v-if="!loading">
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
            :loading="loading"
            :pagination="{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total: number) => `共 ${total} 条记录`,
            }"
            :row-key="rowKey"
            :locale="{
              emptyText: openedBatchIds.length ? '所选批次暂未产生机会数据' : '请选择批次以查看数据',
            }"
            class="opportunities-table"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'id'">
                <a-tag color="processing">{{ record.id }}</a-tag>
              </template>
              
              <template v-else-if="column.key === 'batch_id'">
                <a-tag>{{ record.batch_id ?? '-' }}</a-tag>
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

          <a-card class="mt-4" title="报告列表" size="small">
            <template #extra>
              <span class="text-xs text-gray-500">
                {{ reportForm.batch_id ? `批次 ${reportForm.batch_id}` : '未选择批次' }}
              </span>
            </template>
            <a-table
              :columns="reportColumns"
              :data-source="reports"
              size="small"
              :pagination="false"
              row-key="id"
              :locale="{ emptyText: '该批次暂无报告' }"
            />
          </a-card>
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive, watch } from 'vue';
import api from '../api';
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
  batch_id?: number;
}

interface Batch {
  id: number;
  name: string;
  description?: string;
  last_refreshed_at?: string;
}

interface ReportItem {
  id: number;
  batch_id: number;
  template_id?: number;
  format: string;
  generated_at?: string;
  file_path?: string;
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
    title: '批次',
    dataIndex: 'batch_id',
    key: 'batch_id',
    width: 90,
    align: 'center' as const,
    sorter: (a: Opportunity, b: Opportunity) => (a.batch_id ?? 0) - (b.batch_id ?? 0),
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

const reportColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
  { title: '批次', dataIndex: 'batch_id', key: 'batch_id', width: 80 },
  { title: '模板', dataIndex: 'template_id', key: 'template_id', width: 80 },
  { title: '格式', dataIndex: 'format', key: 'format', width: 80 },
  { title: '生成时间', dataIndex: 'generated_at', key: 'generated_at' },
];

const allOpportunities = ref<Opportunity[]>([]);
const opportunities = ref<Opportunity[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const batches = ref<Batch[]>([]);
const batchesLoading = ref(false);
const openedBatchIds = ref<number[]>([]);
const reports = ref<ReportItem[]>([]);
const reportLoading = ref(false);
const reportForm = reactive({
  batch_id: null as number | null,
  template_id: null as number | null,
  format: 'PDF',
});

const maxProfit = computed(() => {
  if (opportunities.value.length === 0) return 0;
  return Math.max(...opportunities.value.map((opp) => opp.profit_usdt));
});

const avgProfit = computed(() => {
  if (opportunities.value.length === 0) return 0;
  const sum = opportunities.value.reduce((acc, opp) => acc + opp.profit_usdt, 0);
  return sum / opportunities.value.length;
});

const openedBatches = computed(() =>
  batches.value.filter((batch) => openedBatchIds.value.includes(batch.id)),
);

const lastOpenedBatchId = computed(() => {
  if (!openedBatchIds.value.length) return null;
  return openedBatchIds.value[openedBatchIds.value.length - 1];
});

const reportBatchPlaceholder = computed(() => {
  if (lastOpenedBatchId.value) {
    return `默认批次 ${lastOpenedBatchId.value}`;
  }
  return '请输入批次 ID';
});

const rowKey = (record: Opportunity) => `${record.batch_id ?? 'N/A'}-${record.id}`;

const isBatchOpened = (batchId: number) => openedBatchIds.value.includes(batchId);

const applyBatchFilter = () => {
  const ids = openedBatchIds.value;
  if (!ids.length) {
    opportunities.value = [];
    return;
  }
  opportunities.value = allOpportunities.value.filter(
    (opp) => typeof opp.batch_id === 'number' && ids.includes(opp.batch_id),
  );
};

const openBatch = (batchId: number) => {
  if (!isBatchOpened(batchId)) {
    openedBatchIds.value.push(batchId);
  }
  reportForm.batch_id = batchId;
  applyBatchFilter();
};

const closeBatch = (batchId: number) => {
  const idx = openedBatchIds.value.indexOf(batchId);
  if (idx !== -1) {
    openedBatchIds.value.splice(idx, 1);
  }
  if (openedBatchIds.value.length === 0) {
    opportunities.value = [];
  } else {
    applyBatchFilter();
  }
  if (reportForm.batch_id === batchId) {
    const fallback = openedBatchIds.value[openedBatchIds.value.length - 1] ?? null;
    reportForm.batch_id = fallback;
  }
};

const toggleBatch = (batch: Batch) => {
  if (isBatchOpened(batch.id)) {
    closeBatch(batch.id);
  } else {
    openBatch(batch.id);
  }
};

const syncOpenedBatches = () => {
  const available = new Set(batches.value.map((batch) => batch.id));
  openedBatchIds.value = openedBatchIds.value.filter((id) => available.has(id));
  if (reportForm.batch_id && !available.has(reportForm.batch_id)) {
    reportForm.batch_id = openedBatchIds.value[openedBatchIds.value.length - 1] ?? null;
  }
  applyBatchFilter();
};

const fetchOpportunities = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const response = await api.getOpportunities();
    
    if (response.data && response.data.code === 200) {
      allOpportunities.value = response.data.data || [];
    } else {
      error.value = response.data?.message || '获取数据失败，请检查数据格式';
      allOpportunities.value = [];
    }
  } catch (err: any) {
    console.error('获取套利机会失败:', err);
    error.value = err.message || '网络请求失败，请检查后端服务是否可用';
    allOpportunities.value = [];
  } finally {
    loading.value = false;
    applyBatchFilter();
  }
};

const fetchBatches = async () => {
  batchesLoading.value = true;
  try {
    const { data } = await api.getBatches();
    batches.value = data?.data ?? data ?? [];
    syncOpenedBatches();
  } catch (err: any) {
    error.value = err?.message ?? '批次列表获取失败';
  } finally {
    batchesLoading.value = false;
  }
};

const fetchReports = async (batchId?: number | null) => {
  const target = typeof batchId === 'number' ? batchId : reportForm.batch_id;
  if (!target) {
    reports.value = [];
    return;
  }
  try {
    const { data } = await api.getReports({ batch_id: target });
    reports.value = data?.data ?? data ?? [];
  } catch (err: any) {
    error.value = err?.message ?? '报告获取失败';
  }
};

const submitReport = async () => {
  if (!reportForm.batch_id) {
    error.value = '请先选择批次';
    return;
  }
  reportLoading.value = true;
  try {
    await api.createReport({
      batch_id: reportForm.batch_id,
      template_id: reportForm.template_id || undefined,
      format: reportForm.format,
    });
    await fetchReports(reportForm.batch_id);
  } catch (err: any) {
    error.value = err?.message ?? '生成报告失败';
  } finally {
    reportLoading.value = false;
  }
};

const handleRefreshAll = async () => {
  await Promise.all([fetchBatches(), fetchOpportunities()]);
  if (reportForm.batch_id) {
    fetchReports(reportForm.batch_id);
  } else if (openedBatchIds.value.length) {
    fetchReports(openedBatchIds.value[openedBatchIds.value.length - 1]);
  }
};

onMounted(() => {
  fetchBatches().then(() => {
    if (reportForm.batch_id) {
      fetchReports(reportForm.batch_id);
    }
  });
  fetchOpportunities();
});

watch(
  () => reportForm.batch_id,
  (value, prev) => {
    if (value && value !== prev) {
      fetchReports(value);
    }
    if (!value) {
      reports.value = [];
    }
  },
);
</script>

<style scoped>
.page-container {
  padding: 24px;
  background-color: #f0f2f5;
  min-height: 100vh;
}

.main-card {
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
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

.refresh-button {
  background-color: #1890ff;
  border-color: #1890ff;
}
.refresh-button:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

.side-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.batch-list {
  max-height: 360px;
  overflow-y: auto;
}

.batch-item {
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.batch-item.active {
  background-color: #e6f7ff;
}

.batch-info {
  flex: 1;
}

.batch-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
}

.batch-name {
  font-weight: 600;
}

.batch-meta {
  font-size: 12px;
  color: #8c8c8c;
}

.active-batch-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.active-batch-header .actions {
  display: flex;
  gap: 8px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  background-color: #e6f7ff;
  border-left: 5px solid #1890ff;
  border-radius: 8px;
  transition: all 0.3s;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
  transform: translateY(-2px);
}

.price-text {
  font-family: 'Consolas', 'Courier New', monospace;
  font-weight: 600;
  font-size: 14px;
}

.buy-price-text {
  color: #1890ff;
}

.sell-price-text {
  color: #f5222d;
}

.opportunities-table :deep(.ant-table-thead > tr > th) {
  background-color: #e6f7ff;
  color: #0050b3;
  font-weight: 700;
}

.opportunities-table :deep(.ant-table-row:hover) {
  background-color: #f0f8ff !important;
}

.error-alert {
  margin-bottom: 24px;
}

.opened-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
</style>
