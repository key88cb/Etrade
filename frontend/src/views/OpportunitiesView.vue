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

          <a-card title="实验管理 (Experiment)" size="small" class="side-card mt-4">
            <a-alert
              v-if="experimentError"
              :message="experimentError"
              type="error"
              show-icon
              closable
              @close="experimentError = ''"
              class="mb-3"
            />

            <a-form layout="vertical" @finish="createExperiment">
              <a-form-item label="批次 ID" required>
                <a-input-number
                  v-model:value="experimentForm.batch_id"
                  :min="1"
                  style="width: 100%"
                  :placeholder="reportBatchPlaceholder"
                />
              </a-form-item>
              <a-form-item label="实验描述（可选）">
                <a-input v-model:value="experimentForm.description" placeholder="例如：delay=15s, threshold=0.5" />
              </a-form-item>
              <a-button type="primary" html-type="submit" block :loading="experimentsLoading">
                新建实验
              </a-button>
            </a-form>

            <div class="mt-4">
              <div class="text-xs text-gray-500 mb-2 flex items-center justify-between">
                <span>实验列表</span>
                <a-button size="small" @click="refreshExperiments" :loading="experimentsLoading">刷新</a-button>
              </div>
              <a-list
                size="small"
                bordered
                :data-source="experiments"
                :locale="{ emptyText: '暂无实验（请先新建）' }"
                class="batch-list"
              >
                <template #renderItem="{ item }">
                  <a-list-item
                    class="batch-item"
                    :class="{ active: selectedExperimentId === item.id }"
                    @click="selectExperiment(item.id)"
                  >
                    <div class="batch-info">
                      <div class="batch-name">
                        Experiment #{{ item.id }}
                        <a-tag v-if="selectedExperimentId === item.id" color="purple" :bordered="false" style="margin-left: 8px">
                          当前
                        </a-tag>
                      </div>
                      <div class="batch-meta">Batch: {{ item.batch_id }}</div>
                      <div class="batch-meta">{{ item.description || '（无描述）' }}</div>
                    </div>
                    <div class="batch-actions">
                      <a-button type="primary" size="small" ghost @click.stop="selectExperiment(item.id)">
                        选择
                      </a-button>
                    </div>
                  </a-list-item>
                </template>
              </a-list>
            </div>

            <div class="mt-4" v-if="selectedExperimentId">
              <div class="text-xs text-gray-500 mb-2">在当前实验中运行分析模板</div>
              <a-form layout="vertical" @finish="runSelectedExperiment">
                <a-form-item label="Analyse 模板" required>
                  <a-select
                    v-model:value="experimentRunForm.template_id"
                    :loading="templatesLoading"
                    placeholder="选择一个 analyse 模板"
                    :options="analyseTemplateOptions"
                  />
                </a-form-item>
                <a-form-item label="覆盖参数 overrides（JSON，可选）">
                  <a-textarea
                    v-model:value="experimentRunForm.overridesText"
                    :auto-size="{ minRows: 3, maxRows: 6 }"
                    placeholder='例如：{ "overwrite": false, "strategy": { "profit_threshold": 1, "time_delay_seconds": 15 } }'
                  />
                </a-form-item>
                <a-button type="primary" html-type="submit" block :loading="runLoading" :disabled="!experimentRunForm.template_id">
                  运行实验
                </a-button>
              </a-form>
              <div v-if="lastRunTaskId" class="text-xs text-gray-500 mt-2">
                最近触发任务：<span class="font-mono">{{ lastRunTaskId }}</span>
                <a class="ml-2" @click="goTasks">去任务中心查看</a>
              </div>
            </div>
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
            <a-col :xs="24" :sm="6">
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
            <a-col :xs="24" :sm="6">
              <a-card :bordered="false" class="stat-card stat-max">
                <div class="flex items-start justify-between">
                  <div>
                    <div class="text-xs text-gray-500">最大 / 中位利润</div>
                    <div class="text-lg font-semibold text-green-600 mt-1">
                      {{ (maxProfit ?? 0).toFixed(4) }} <span class="text-xs font-normal text-gray-500">USDT</span>
                    </div>
                    <div class="text-sm text-purple-600 mt-1">
                      Median: {{ (medianProfit ?? 0).toFixed(4) }}
                    </div>
                  </div>
                  <TrophyOutlined class="text-green-500 text-lg" />
                </div>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="6">
              <a-card :bordered="false" class="stat-card stat-avg">
                <a-statistic
                  title="平均风险分"
                  :value="avgRiskScore"
                  :precision="1"
                  :value-style="{ color: '#fa8c16' }"
                />
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="6">
              <a-card :bordered="false" class="stat-card stat-avg">
                <div class="text-xs text-gray-500">时间范围 / 批次数</div>
                <div class="text-sm text-gray-800 mt-1">
                  {{ opportunityTimeRangeLabel }}
                </div>
                <div class="text-xs text-gray-500 mt-2">
                  批次数：{{ openedBatchIds.length }}
                </div>
              </a-card>
            </a-col>
          </a-row>

          <a-row :gutter="16" class="mb-4" v-if="!loading">
            <a-col :xs="24" :lg="8">
              <a-card size="small" title="利润分布" class="shadow-sm">
                <div ref="profitHistRef" style="height: 240px;"></div>
              </a-card>
            </a-col>
            <a-col :xs="24" :lg="8">
              <a-card size="small" title="利润 vs 风险 (Scatter)" class="shadow-sm">
                <div ref="profitRiskScatterRef" style="height: 240px;"></div>
              </a-card>
            </a-col>
            <a-col :xs="24" :lg="8">
              <a-card size="small" title="利润随时间" class="shadow-sm">
                <div ref="profitTimeRef" style="height: 240px;"></div>
              </a-card>
            </a-col>
          </a-row>

          <a-row :gutter="16" class="mb-4" v-if="!loading && openedBatchIds.length">
            <a-col :xs="24" :lg="14">
              <a-card size="small" title="多批次利润分布对比（Boxplot）" class="shadow-sm">
                <div ref="batchProfitCompareRef" style="height: 260px;"></div>
              </a-card>
            </a-col>
            <a-col :xs="24" :lg="10">
              <a-card size="small" title="多批次平均风险对比" class="shadow-sm">
                <div ref="batchRiskCompareRef" style="height: 260px;"></div>
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
            :customRow="(record: Opportunity) => ({ onClick: () => openDetails(record) })"
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

              <template v-else-if="column.key === 'risk_score'">
                <div v-if="record.risk_metrics">
                  <a-tag :color="getRiskColor(record.risk_metrics.risk_score)">
                    {{ record.risk_metrics.risk_score }}
                  </a-tag>
                  <div class="text-xs text-gray-400 mt-1">
                    滑点: {{ record.risk_metrics.estimated_slippage_pct }}%
                  </div>
                </div>
                <span v-else class="text-gray-300">-</span>
              </template>

              <template v-else-if="column.key === 'action'">
                <a-button size="small" type="link" @click.stop="openDetails(record)">详情</a-button>
              </template>
            </template>
          </a-table>

          <a-card class="mt-4" title="实验运行记录" size="small" v-if="selectedExperimentId">
            <template #extra>
              <div class="text-xs text-gray-500 flex items-center gap-2">
                <span>Experiment #{{ selectedExperimentId }}</span>
                <a-button size="small" @click="fetchExperimentRuns(selectedExperimentId)" :loading="runsLoading">刷新</a-button>
              </div>
            </template>
            <a-table
              :columns="experimentRunColumns"
              :data-source="experimentRuns"
              size="small"
              row-key="id"
              :pagination="false"
              :locale="{ emptyText: '暂无运行记录' }"
            />
          </a-card>

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

    <a-modal
      v-model:open="detailsOpen"
      :title="selectedOpp ? `机会详情 #${selectedOpp.id}` : '机会详情'"
      width="920px"
      :footer="null"
      @afterOpenChange="onDetailsOpenChange"
    >
      <div v-if="selectedOpp" class="space-y-4">
        <a-row :gutter="16">
          <a-col :xs="24" :lg="10">
            <a-card size="small" title="关键信息" :bordered="false">
              <a-descriptions size="small" :column="1">
                <a-descriptions-item label="批次">{{ selectedOpp.batch_id ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="方向">{{ selectedOpp.buy_platform }} → {{ selectedOpp.sell_platform }}</a-descriptions-item>
                <a-descriptions-item label="净利润(USDT)">{{ selectedOpp.profit_usdt }}</a-descriptions-item>
                <a-descriptions-item label="block_time">{{ selectedOpp.details?.block_time ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="experiment_id">{{ selectedOpp.details?.experiment_id ?? '-' }}</a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>
          <a-col :xs="24" :lg="14">
            <a-card size="small" title="风险可视化（Gauge / Radar）" :bordered="false">
              <a-row :gutter="12">
                <a-col :xs="24" :sm="10">
                  <div ref="riskGaugeRef" style="height: 220px;"></div>
                </a-col>
                <a-col :xs="24" :sm="14">
                  <div ref="riskRadarRef" style="height: 220px;"></div>
                </a-col>
              </a-row>
            </a-card>
          </a-col>
        </a-row>

        <a-card size="small" title="价格上下文（mini）" :bordered="false">
          <div ref="miniPriceRef" style="height: 260px;"></div>
        </a-card>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive, watch, nextTick, onBeforeUnmount } from 'vue';
import api from '../api';
import { message } from 'ant-design-vue';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import {
  DollarOutlined,
  ReloadOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RiseOutlined,
  DatabaseOutlined,
  TrophyOutlined,
} from '@ant-design/icons-vue';

interface RiskMetrics {
  risk_score: number;
  volatility: number;
  estimated_slippage_pct: number;
  market_volume_eth: number;
}

interface Opportunity {
  id: number;
  buy_platform: string;
  sell_platform: string;
  buy_price: number;
  sell_price: number;
  profit_usdt: number;
  batch_id?: number;
  risk_metrics?: RiskMetrics;
  details?: {
    block_time?: string;
    experiment_id?: string | number;
  };
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

interface Experiment {
  id: number;
  batch_id: number;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

interface ExperimentRun {
  id: number;
  experiment_id: number;
  template_id: number;
  task_id: number;
  metrics?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

interface TemplateItem {
  id: number;
  name: string;
  task_type: string;
  config?: Record<string, unknown>;
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
  {
    title: '风险评分',
    dataIndex: ['risk_metrics', 'risk_score'],
    key: 'risk_score',
    width: 120,
    align: 'center' as const,
    sorter: (a: Opportunity, b: Opportunity) => 
      (a.risk_metrics?.risk_score ?? 0) - (b.risk_metrics?.risk_score ?? 0),
  },
  {
    title: '操作',
    key: 'action',
    width: 90,
    align: 'center' as const,
  },
];

const reportColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
  { title: '批次', dataIndex: 'batch_id', key: 'batch_id', width: 80 },
  { title: '模板', dataIndex: 'template_id', key: 'template_id', width: 80 },
  { title: '格式', dataIndex: 'format', key: 'format', width: 80 },
  { title: '生成时间', dataIndex: 'generated_at', key: 'generated_at' },
];

const experimentRunColumns = [
  { title: 'Run ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: 'Template', dataIndex: 'template_id', key: 'template_id', width: 90 },
  { title: 'Task(ID)', dataIndex: 'task_id', key: 'task_id', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
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

// Experiments
const router = useRouter();
const experiments = ref<Experiment[]>([]);
const experimentsLoading = ref(false);
const experimentError = ref('');
const selectedExperimentId = ref<number | null>(null);
const experimentRuns = ref<ExperimentRun[]>([]);
const runsLoading = ref(false);
const templatesLoading = ref(false);
const analyseTemplates = ref<TemplateItem[]>([]);
const runLoading = ref(false);
const lastRunTaskId = ref<string>('');

const experimentForm = reactive({
  batch_id: null as number | null,
  description: '',
});

const experimentRunForm = reactive({
  template_id: null as number | null,
  overridesText: '',
});

const maxProfit = computed(() => {
  if (opportunities.value.length === 0) return 0;
  return Math.max(...opportunities.value.map((opp) => opp.profit_usdt));
});

const medianProfit = computed(() => {
  const list = opportunities.value.map((o) => o.profit_usdt).slice().sort((a, b) => a - b);
  if (!list.length) return 0;
  const mid = Math.floor(list.length / 2);
  if (list.length % 2 === 0) {
    const a = list[mid - 1] ?? 0;
    const b = list[mid] ?? 0;
    return (a + b) / 2;
  }
  return list[mid] ?? 0;
});

const avgRiskScore = computed(() => {
  const scores = opportunities.value
    .map((o) => o.risk_metrics?.risk_score)
    .filter((v): v is number => typeof v === 'number');
  if (!scores.length) return 0;
  return scores.reduce((a, b) => a + b, 0) / scores.length;
});

const opportunityTimeRangeLabel = computed(() => {
  const times = opportunities.value
    .map((o) => (o.details?.block_time ? new Date(o.details.block_time).getTime() : NaN))
    .filter((t) => Number.isFinite(t)) as number[];
  if (!times.length) return '--';
  const min = new Date(Math.min(...times));
  const max = new Date(Math.max(...times));
  return `${min.toLocaleString()} ~ ${max.toLocaleString()}`;
});

const profitHistRef = ref<HTMLDivElement | null>(null);
const profitRiskScatterRef = ref<HTMLDivElement | null>(null);
const profitTimeRef = ref<HTMLDivElement | null>(null);
const batchProfitCompareRef = ref<HTMLDivElement | null>(null);
const batchRiskCompareRef = ref<HTMLDivElement | null>(null);

let profitHistChart: echarts.ECharts | null = null;
let profitRiskChart: echarts.ECharts | null = null;
let profitTimeChart: echarts.ECharts | null = null;
let batchProfitCompareChart: echarts.ECharts | null = null;
let batchRiskCompareChart: echarts.ECharts | null = null;

const detailsOpen = ref(false);
const selectedOpp = ref<Opportunity | null>(null);
const riskGaugeRef = ref<HTMLDivElement | null>(null);
const riskRadarRef = ref<HTMLDivElement | null>(null);
const miniPriceRef = ref<HTMLDivElement | null>(null);
let riskGaugeChart: echarts.ECharts | null = null;
let riskRadarChart: echarts.ECharts | null = null;
let miniPriceChart: echarts.ECharts | null = null;

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

const analyseTemplateOptions = computed(() =>
  analyseTemplates.value.map((tpl) => ({
    label: `#${tpl.id} · ${tpl.name}`,
    value: tpl.id,
  })),
);

const rowKey = (record: Opportunity) => `${record.batch_id ?? 'N/A'}-${record.id}`;

const isBatchOpened = (batchId: number) => openedBatchIds.value.includes(batchId);

const getRiskColor = (score: number) => {
  if (score >= 80) return 'green';
  if (score >= 60) return 'orange';
  return 'red';
};

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
      const data = response.data.data;
      // 兼容后端返回 { items: [], pagination: {} } 或直接返回 [] 的情况
      const normalizeItem = (raw: any): Opportunity => ({
        ...raw,
        details: raw?.details ?? raw?.DetailsJSON ?? raw?.details_json ?? undefined,
        risk_metrics: raw?.risk_metrics ?? raw?.RiskMetricsJSON ?? raw?.risk_metrics_json ?? raw?.riskMetrics ?? undefined,
      });
      if (Array.isArray(data)) {
        allOpportunities.value = data.map(normalizeItem);
      } else if (data && Array.isArray(data.items)) {
        allOpportunities.value = data.items.map(normalizeItem);
      } else {
        allOpportunities.value = [];
      }
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
    nextTick(() => {
      renderOverviewCharts();
      renderBatchCompareCharts();
    });
  }
};

const ensureChart = (el: HTMLDivElement | null, instance: echarts.ECharts | null) => {
  if (!el) return null;
  if (instance) return instance;
  return echarts.init(el);
};

const quantile = (sorted: number[], q: number) => {
  if (!sorted.length) return 0;
  if (q <= 0) return sorted[0] ?? 0;
  if (q >= 1) return sorted[sorted.length - 1] ?? 0;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  const baseVal = sorted[base] ?? 0;
  const nextVal = sorted[base + 1] ?? baseVal;
  return baseVal + rest * (nextVal - baseVal);
};

const renderOverviewCharts = () => {
  // Profit histogram
  profitHistChart = ensureChart(profitHistRef.value, profitHistChart);
  if (profitHistChart) {
    const profits = opportunities.value.map((o) => o.profit_usdt).filter((v) => Number.isFinite(v));
    if (!profits.length) {
      profitHistChart.clear();
    } else {
      const min = Math.min(...profits);
      const max = Math.max(...profits);
      const bins = 18;
      const step = (max - min) / bins || 1;
      const edges = Array.from({ length: bins }, (_, i) => min + i * step);
      const counts = new Array(bins).fill(0);
      for (const p of profits) {
        const idx = Math.min(bins - 1, Math.max(0, Math.floor((p - min) / step)));
        counts[idx] += 1;
      }
      const labels = edges.map((e) => e.toFixed(1));
      profitHistChart.setOption({
        tooltip: { trigger: 'axis' },
        toolbox: { feature: { saveAsImage: {} } },
        grid: { left: 44, right: 14, top: 18, bottom: 40 },
        xAxis: { type: 'category', data: labels, axisLabel: { rotate: 35, fontSize: 10 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: counts, itemStyle: { color: '#1890ff' } }],
      });
    }
  }

  // Scatter profit vs risk
  profitRiskChart = ensureChart(profitRiskScatterRef.value, profitRiskChart);
  if (profitRiskChart) {
    const points = opportunities.value
      .filter((o) => o.risk_metrics && typeof o.risk_metrics.risk_score === 'number')
      .map((o) => [o.risk_metrics!.risk_score, o.profit_usdt, o.risk_metrics!.market_volume_eth ?? 0]);
    profitRiskChart.setOption({
      tooltip: { trigger: 'item' },
      toolbox: { feature: { saveAsImage: {} } },
      grid: { left: 50, right: 18, top: 18, bottom: 40 },
      xAxis: { type: 'value', name: 'risk_score', min: 0, max: 100 },
      yAxis: { type: 'value', name: 'profit_usdt' },
      visualMap: {
        type: 'continuous',
        dimension: 0,
        min: 0,
        max: 100,
        right: 10,
        top: 10,
        inRange: { color: ['#52c41a', '#fa8c16', '#f5222d'] },
      },
      series: [
        {
          type: 'scatter',
          data: points,
          symbolSize: (val: any) => {
            const volume = Number(val[2] ?? 0);
            return Math.max(6, Math.min(24, Math.sqrt(volume) * 4));
          },
        },
      ],
    });
  }

  // Profit over time
  profitTimeChart = ensureChart(profitTimeRef.value, profitTimeChart);
  if (profitTimeChart) {
    const timeData = opportunities.value
      .map((o) => {
        const t = o.details?.block_time ? new Date(o.details.block_time).getTime() : NaN;
        return Number.isFinite(t) ? [t, o.profit_usdt] : null;
      })
      .filter((v): v is [number, number] => Array.isArray(v));
    timeData.sort((a, b) => a[0] - b[0]);
    profitTimeChart.setOption({
      tooltip: { trigger: 'axis' },
      toolbox: { feature: { dataZoom: { yAxisIndex: 'none' }, restore: {}, saveAsImage: {} } },
      grid: { left: 50, right: 18, top: 18, bottom: 40 },
      xAxis: { type: 'time' },
      yAxis: { type: 'value', name: 'profit_usdt' },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
      series: [
        {
          type: 'line',
          data: timeData,
          showSymbol: false,
          smooth: true,
          lineStyle: { width: 2, color: '#722ed1' },
          areaStyle: { opacity: 0.12, color: '#722ed1' },
        },
      ],
    });
  }
};

const renderBatchCompareCharts = () => {
  batchProfitCompareChart = ensureChart(batchProfitCompareRef.value, batchProfitCompareChart);
  batchRiskCompareChart = ensureChart(batchRiskCompareRef.value, batchRiskCompareChart);

  const groups = new Map<number, Opportunity[]>();
  for (const opp of opportunities.value) {
    if (typeof opp.batch_id !== 'number') continue;
    const existing = groups.get(opp.batch_id) ?? [];
    existing.push(opp);
    groups.set(opp.batch_id, existing);
  }
  const batchIds = Array.from(groups.keys()).sort((a, b) => a - b);
  const labels = batchIds.map((id) => `#${id}`);

  if (batchProfitCompareChart) {
    if (!batchIds.length) {
      batchProfitCompareChart.clear();
    } else {
      const boxData: number[][] = [];
      const outliers: [number, number][] = [];
      batchIds.forEach((batchId, idx) => {
        const profits = (groups.get(batchId) ?? [])
          .map((o) => o.profit_usdt)
          .filter((v) => Number.isFinite(v))
          .slice()
          .sort((a, b) => a - b);
        if (!profits.length) {
          boxData.push([0, 0, 0, 0, 0]);
          return;
        }
        const q1 = quantile(profits, 0.25);
        const q2 = quantile(profits, 0.5);
        const q3 = quantile(profits, 0.75);
        const iqr = q3 - q1;
        const low = q1 - 1.5 * iqr;
        const high = q3 + 1.5 * iqr;
        for (const p of profits) {
          if (p < low || p > high) outliers.push([idx, p]);
        }
        boxData.push([profits[0] ?? 0, q1, q2, q3, profits[profits.length - 1] ?? 0]);
      });

      batchProfitCompareChart.setOption({
        tooltip: { trigger: 'item' },
        toolbox: { feature: { saveAsImage: {} } },
        grid: { left: 44, right: 14, top: 18, bottom: 40 },
        xAxis: { type: 'category', data: labels, axisLabel: { rotate: 25 } },
        yAxis: { type: 'value', name: 'profit_usdt' },
        series: [
          { name: 'profit box', type: 'boxplot', data: boxData, itemStyle: { color: '#1890ff' } },
          { name: 'outlier', type: 'scatter', data: outliers, symbolSize: 6, itemStyle: { color: '#f5222d' } },
        ],
      });
    }
  }

  if (batchRiskCompareChart) {
    if (!batchIds.length) {
      batchRiskCompareChart.clear();
    } else {
      const avgRisk = batchIds.map((batchId) => {
        const list = (groups.get(batchId) ?? [])
          .map((o) => o.risk_metrics?.risk_score)
          .filter((v): v is number => typeof v === 'number');
        if (!list.length) return 0;
        return list.reduce((a, b) => a + b, 0) / list.length;
      });
      batchRiskCompareChart.setOption({
        tooltip: { trigger: 'axis' },
        toolbox: { feature: { saveAsImage: {} } },
        grid: { left: 44, right: 14, top: 18, bottom: 40 },
        xAxis: { type: 'category', data: labels, axisLabel: { rotate: 25 } },
        yAxis: { type: 'value', min: 0, max: 100, name: 'avg risk_score' },
        series: [
          {
            type: 'bar',
            data: avgRisk,
            itemStyle: { color: '#fa8c16' },
            label: { show: true, position: 'top', formatter: ({ value }: any) => Number(value).toFixed(1) },
          },
        ],
      });
    }
  }
};

const openDetails = (record: Opportunity) => {
  selectedOpp.value = record;
  detailsOpen.value = true;
};

const onDetailsOpenChange = (open: boolean) => {
  if (open) renderDetailCharts();
  else disposeDetailCharts();
};

const disposeDetailCharts = () => {
  riskGaugeChart?.dispose();
  riskGaugeChart = null;
  riskRadarChart?.dispose();
  riskRadarChart = null;
  miniPriceChart?.dispose();
  miniPriceChart = null;
};

const renderDetailCharts = async () => {
  if (!selectedOpp.value) return;

  if (riskGaugeRef.value) {
    riskGaugeChart = ensureChart(riskGaugeRef.value, riskGaugeChart);
    const rm = selectedOpp.value.risk_metrics;
    const risk = rm?.risk_score ?? 0;
    riskGaugeChart?.setOption({
      series: [
        {
          type: 'gauge',
          min: 0,
          max: 100,
          progress: { show: true, width: 12 },
          axisLine: { lineStyle: { width: 12 } },
          axisTick: { show: false },
          splitLine: { length: 10 },
          axisLabel: { distance: 14 },
          pointer: { show: false },
          title: { show: true, offsetCenter: [0, '60%'], fontSize: 12 },
          detail: { valueAnimation: true, formatter: '{value}', fontSize: 18, offsetCenter: [0, '20%'] },
          data: [{ value: risk, name: 'risk_score' }],
        },
      ],
    });
  }

  if (riskRadarRef.value) {
    riskRadarChart = ensureChart(riskRadarRef.value, riskRadarChart);
    const rm = selectedOpp.value.risk_metrics;
    const risk = rm?.risk_score ?? 0;
    const vol = rm?.volatility ?? 0;
    const slip = rm?.estimated_slippage_pct ?? 0;
    const volMax = 0.05;
    const slipMax = 5;
    riskRadarChart?.setOption({
      tooltip: {},
      radar: {
        indicator: [
          { name: 'risk_score', max: 100 },
          { name: 'volatility', max: volMax },
          { name: 'slippage_%', max: slipMax },
        ],
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: [risk, Math.min(vol, volMax), Math.min(slip, slipMax)],
              areaStyle: { opacity: 0.2 },
            },
          ],
        },
      ],
    });
  }

  if (miniPriceRef.value) {
    miniPriceChart = ensureChart(miniPriceRef.value, miniPriceChart);
    const bt = selectedOpp.value.details?.block_time ? new Date(selectedOpp.value.details.block_time).getTime() : NaN;
    if (!Number.isFinite(bt)) {
      miniPriceChart?.clear();
      miniPriceChart?.setOption({ title: { text: '无 block_time，无法加载价格上下文', left: 'center' } });
      return;
    }
    const start = bt - 15 * 60 * 1000;
    const end = bt + 15 * 60 * 1000;
    try {
      const { data } = await api.getPriceComparisonData({ startTime: start, endTime: end });
      const payload = data?.data ?? {};
      const uniswap = (payload.uniswap ?? []).map((p: any) => [p[0], Number(p[1])]);
      const binance = (payload.binance ?? []).map((p: any) => [p[0], Number(p[1])]);
      miniPriceChart?.setOption({
        tooltip: { trigger: 'axis' },
        legend: { top: 0, data: ['Uniswap', 'Binance'] },
        grid: { left: 50, right: 18, top: 30, bottom: 30 },
        xAxis: { type: 'time' },
        yAxis: { type: 'value', scale: true },
        dataZoom: [{ type: 'inside' }],
        series: [
          { name: 'Uniswap', type: 'line', showSymbol: false, data: uniswap, lineStyle: { width: 1.5 } },
          { name: 'Binance', type: 'line', showSymbol: false, data: binance, lineStyle: { width: 1.5 } },
        ],
      });
    } catch {
      miniPriceChart?.clear();
      miniPriceChart?.setOption({ title: { text: '价格数据加载失败', left: 'center' } });
    }
  }
};

watch(
  () => opportunities.value,
  () => {
    nextTick(() => {
      renderOverviewCharts();
      renderBatchCompareCharts();
    });
  },
  { deep: true },
);

onBeforeUnmount(() => {
  profitHistChart?.dispose();
  profitRiskChart?.dispose();
  profitTimeChart?.dispose();
  batchProfitCompareChart?.dispose();
  batchRiskCompareChart?.dispose();
  disposeDetailCharts();
});

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

const fetchTemplates = async () => {
  templatesLoading.value = true;
  try {
    const { data } = await api.getTemplates();
    const items = (data?.data ?? data ?? []) as any[];
    analyseTemplates.value = items
      .map((tpl) => ({
        id: tpl.id ?? tpl.ID,
        name: tpl.name ?? tpl.Name,
        task_type: tpl.task_type ?? tpl.TaskType,
        config: tpl.config ?? tpl.ConfigJSON ?? {},
      }))
      .filter((tpl) => tpl.task_type === 'analyse');
  } catch (err: any) {
    experimentError.value = err?.message ?? '模板加载失败';
  } finally {
    templatesLoading.value = false;
  }
};

const refreshExperiments = async () => {
  const batchId = experimentForm.batch_id ?? reportForm.batch_id ?? lastOpenedBatchId.value;
  if (!batchId) return;
  experimentsLoading.value = true;
  experimentError.value = '';
  try {
    const { data } = await api.getExperiments({ batch_id: batchId });
    experiments.value = data?.data ?? data ?? [];
  } catch (err: any) {
    experimentError.value = err?.message ?? '实验列表获取失败';
  } finally {
    experimentsLoading.value = false;
  }
};

const createExperiment = async () => {
  const batchId = experimentForm.batch_id ?? reportForm.batch_id ?? lastOpenedBatchId.value;
  if (!batchId) {
    experimentError.value = '请先选择批次 ID';
    return;
  }
  experimentsLoading.value = true;
  experimentError.value = '';
  try {
    const { data } = await api.createExperiment({
      batch_id: batchId,
      description: experimentForm.description || undefined,
    });
    const exp = data?.data ?? data;
    message.success(`实验已创建：#${exp?.id ?? ''}`);
    experimentForm.batch_id = batchId;
    experimentForm.description = '';
    await refreshExperiments();
    if (exp?.id) {
      selectExperiment(exp.id);
    }
  } catch (err: any) {
    experimentError.value = err?.message ?? '创建实验失败';
  } finally {
    experimentsLoading.value = false;
  }
};

const fetchExperimentRuns = async (experimentId: number) => {
  runsLoading.value = true;
  try {
    const { data } = await api.getExperimentRuns(experimentId);
    experimentRuns.value = data?.data ?? data ?? [];
  } catch (err: any) {
    experimentError.value = err?.message ?? '实验运行记录获取失败';
  } finally {
    runsLoading.value = false;
  }
};

const selectExperiment = async (id: number) => {
  selectedExperimentId.value = id;
  lastRunTaskId.value = '';
  await fetchExperimentRuns(id);
};

const runSelectedExperiment = async () => {
  if (!selectedExperimentId.value) return;
  if (!experimentRunForm.template_id) {
    experimentError.value = '请选择 analyse 模板';
    return;
  }
  let overrides: Record<string, unknown> | undefined;
  if (experimentRunForm.overridesText.trim()) {
    try {
      overrides = JSON.parse(experimentRunForm.overridesText);
    } catch {
      experimentError.value = 'overrides 必须是合法 JSON';
      return;
    }
  }

  runLoading.value = true;
  experimentError.value = '';
  try {
    const { data } = await api.runExperiment(selectedExperimentId.value, {
      template_id: experimentRunForm.template_id,
      overrides,
      trigger: 'ui',
    });
    const payload = data?.data ?? data ?? {};
    const taskId = payload?.task?.task_id ?? payload?.task?.TaskID ?? '';
    if (taskId) {
      lastRunTaskId.value = String(taskId);
    }
    message.success('实验已触发运行（任务已入队）');
    await fetchExperimentRuns(selectedExperimentId.value);
  } catch (err: any) {
    experimentError.value = err?.message ?? '运行实验失败';
  } finally {
    runLoading.value = false;
  }
};

const goTasks = () => {
  router.push('/tasks');
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
  fetchTemplates();
});

watch(
  () => reportForm.batch_id,
  (value, prev) => {
    if (value && value !== prev) {
      fetchReports(value);
      // 自动同步实验批次：如果用户未手动选择实验批次，则跟随当前批次
      if (!experimentForm.batch_id) {
        experimentForm.batch_id = value;
      }
    }
    if (!value) {
      reports.value = [];
    }
  },
);

watch(
  () => experimentForm.batch_id,
  (value, prev) => {
    if (value && value !== prev) {
      refreshExperiments();
    }
  },
);
</script>

<style scoped>
:global(:root) {
  --gh-bg: #f6f8fa;
  --gh-surface: #ffffff;
  --gh-border: #d0d7de;
  --gh-muted: #57606a;
  --gh-accent: #0969da;
  --gh-selected: #ddf4ff;
  --gh-hover: #f6f8fa;
  --gh-table-head: #f6f8fa;
}

:global(.dark) {
  --gh-bg: #0d1117;
  --gh-surface: #161b22;
  --gh-border: #30363d;
  --gh-muted: #7d8590;
  --gh-accent: #58a6ff;
  --gh-selected: rgba(31, 111, 235, 0.15);
  --gh-hover: #161b22;
  --gh-table-head: #0d1117;
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

.refresh-button {}

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
  background-color: var(--gh-selected);
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
  color: var(--gh-muted);
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
  background-color: rgba(9, 105, 218, 0.08);
  border-left: 4px solid var(--gh-accent);
  border-radius: 8px;
  transition: all 0.3s;
}

:global(.dark) .stat-card {
  background-color: rgba(88, 166, 255, 0.12);
}

.stat-card:hover {
  box-shadow: 0 1px 0 rgba(27, 31, 36, 0.04);
  transform: translateY(-2px);
}

.price-text {
  font-family: 'Consolas', 'Courier New', monospace;
  font-weight: 600;
  font-size: 14px;
}

.buy-price-text {
  color: var(--gh-accent);
}

.sell-price-text {
  color: #f5222d;
}

.opportunities-table :deep(.ant-table-thead > tr > th) {
  background-color: var(--gh-table-head);
  color: var(--gh-muted);
  font-weight: 700;
}

.opportunities-table :deep(.ant-table-row:hover) {
  background-color: var(--gh-hover) !important;
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
