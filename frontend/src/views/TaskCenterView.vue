<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { message } from 'ant-design-vue';
import * as echarts from 'echarts';
import api from '../api';

interface TaskItem {
  task_id: string;
  type: string;
  status: string;
  trigger: string;
  queued_at?: string;
  started_at?: string;
  finished_at?: string;
}

interface TaskDetail extends TaskItem {
  config: Record<string, unknown>;
  log_summary?: string;
  duration_secs?: number;
}

type TaskLog = { timestamp: string; level: string; message: string };

const STATUS_META: Record<string, { label: string; color: string }> = {
  WAIT: { label: 'WAIT', color: 'default' },
  RUNNING: { label: 'RUNNING', color: 'processing' },
  SUCCESS: { label: 'SUCCESS', color: 'success' },
  FAILED: { label: 'FAILED', color: 'error' },
  CANCELLED: { label: 'CANCELLED', color: 'warning' },
  CANCELED: { label: 'CANCELLED', color: 'warning' },
};

const normalizeStatus = (status?: string) => (status ?? '').toUpperCase();
const statusLabel = (status?: string) => STATUS_META[normalizeStatus(status)]?.label ?? (status ?? '-');
const statusColor = (status?: string) => STATUS_META[normalizeStatus(status)]?.color ?? 'default';

const tasks = ref<TaskItem[]>([]);
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0,
});
const loading = ref(false);
const selectedTask = ref<TaskDetail | null>(null);
const taskLogs = ref<TaskLog[]>([]);
const logLoading = ref(false);
const errorMessage = ref('');

const statusChartRef = ref<HTMLDivElement | null>(null);
let statusChart: echarts.ECharts | null = null;
const detailAnchorRef = ref<HTMLDivElement | null>(null);

const cancelOpen = ref(false);
const cancelReason = ref('');
const cancelLoading = ref(false);

const latestLogs = computed(() => taskLogs.value.slice(0, 5));

const statusCounts = computed(() => {
  const counts: Record<string, number> = {};
  for (const task of tasks.value) {
    const key = normalizeStatus(task.status);
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
});

const totalTasks = computed(() => pagination.total ?? tasks.value.length);
const countOf = (key: string) => statusCounts.value[key] ?? 0;

const isCancelable = computed(() => {
  const st = normalizeStatus(selectedTask.value?.status);
  return Boolean(selectedTask.value?.task_id) && !['SUCCESS', 'FAILED', 'CANCELLED', 'CANCELED'].includes(st);
});

const fetchTasks = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getTasks({ page: pagination.page, limit: pagination.limit });
    tasks.value = data?.data?.items ?? [];
    const pager = data?.data?.pagination;
    if (pager) {
      pagination.total = pager.total ?? 0;
      pagination.page = pager.page ?? pagination.page;
      pagination.limit = pager.limit ?? pagination.limit;
    }
  } catch (error: any) {
    errorMessage.value = error?.message ?? '任务列表获取失败';
  } finally {
    loading.value = false;
    nextTick(renderStatusChart);
  }
};

const viewTask = async (taskId: string) => {
  if (!taskId) {
    message.warning('task_id 为空');
    return;
  }
  selectedTask.value = null;
  taskLogs.value = [];
  message.loading({ content: '加载任务详情…', key: 'task-detail' });
  try {
    const { data } = await api.getTaskDetail(taskId);
    selectedTask.value = data?.data ?? data;
    await fetchLogs(taskId, 5);
    message.success({ content: '已加载任务详情', key: 'task-detail', duration: 1.2 });
    nextTick(() => detailAnchorRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  } catch (error: any) {
    errorMessage.value = error?.message ?? '任务详情获取失败';
    message.error({ content: errorMessage.value, key: 'task-detail' });
  }
};

const fetchLogs = async (taskId: string, limit?: number) => {
  logLoading.value = true;
  try {
    const { data } = await api.getTaskLogs(taskId, limit ? { limit } : undefined);
    const list = data?.data?.items ?? data?.items ?? [];
    taskLogs.value = Array.isArray(list) ? list : [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '任务日志获取失败';
  } finally {
    logLoading.value = false;
  }
};

const exportStatusChart = () => {
  if (!statusChart) {
    message.warning('图表未初始化');
    return;
  }
  try {
    const isDark = document.documentElement.classList.contains('dark');
    const url = statusChart.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: isDark ? '#0d1117' : '#ffffff',
    });
    const a = document.createElement('a');
    a.href = url;
    a.download = `task-status-${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    message.success('已导出图片');
  } catch (err: any) {
    message.error(err?.message ?? '导出失败');
  }
};

const renderStatusChart = () => {
  if (!statusChartRef.value) return;
  if (!statusChart) statusChart = echarts.init(statusChartRef.value);

  const data = [
    { name: 'WAIT', value: countOf('WAIT') },
    { name: 'RUNNING', value: countOf('RUNNING') },
    { name: 'SUCCESS', value: countOf('SUCCESS') },
    { name: 'FAILED', value: countOf('FAILED') },
    { name: 'CANCELLED', value: countOf('CANCELLED') + countOf('CANCELED') },
  ].filter((x) => x.value > 0);

  statusChart.setOption({
    tooltip: { trigger: 'item' },
    toolbox: { feature: { saveAsImage: { pixelRatio: 2 } } },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '45%'],
        data,
        label: { formatter: '{b}: {c}' },
      },
    ],
  });
};

const openCancel = () => {
  cancelReason.value = '';
  cancelOpen.value = true;
};

const submitCancel = async () => {
  if (!selectedTask.value?.task_id) return;
  cancelLoading.value = true;
  try {
    await api.cancelTask(selectedTask.value.task_id, cancelReason.value ? { reason: cancelReason.value } : undefined);
    message.success('已提交取消请求');
    cancelOpen.value = false;
    await viewTask(selectedTask.value.task_id);
    await fetchTasks();
  } catch (error: any) {
    message.error(error?.message ?? '取消任务失败');
  } finally {
    cancelLoading.value = false;
  }
};

const onTaskTableChange = (pager: any) => {
  pagination.page = pager?.current ?? pagination.page;
  pagination.limit = pager?.pageSize ?? pagination.limit;
  fetchTasks();
};

watch(
  () => tasks.value,
  () => nextTick(renderStatusChart),
  { deep: true },
);

onMounted(fetchTasks);

onBeforeUnmount(() => {
  statusChart?.dispose();
  statusChart = null;
});
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <div class="text-xl font-semibold text-[#24292f] dark:text-[#e6edf3]">任务中心</div>
        <div class="text-sm text-[#57606a] dark:text-[#7d8590]">查看任务状态、时间线与日志（支持取消任务）</div>
      </div>
      <a-button type="primary" :loading="loading" @click="fetchTasks">刷新</a-button>
    </div>

    <a-alert v-if="errorMessage" type="error" show-icon :message="errorMessage" />

    <a-row :gutter="16">
      <a-col :xs="24" :sm="8" :lg="4">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="总任务" :value="totalTasks" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="4">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="WAIT" :value="countOf('WAIT')" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="4">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="RUNNING" :value="countOf('RUNNING')" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="4">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="SUCCESS" :value="countOf('SUCCESS')" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="4">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="FAILED" :value="countOf('FAILED')" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8" :lg="4">
        <a-card size="small" :bordered="false" class="shadow-sm">
          <a-statistic title="CANCELLED" :value="countOf('CANCELLED') + countOf('CANCELED')" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16">
        <a-col :xs="24" :lg="10">
          <a-card size="small" title="状态分布" class="shadow-sm">
            <template #extra>
              <a-button size="small" @click="exportStatusChart">导出图片</a-button>
            </template>
            <div ref="statusChartRef" style="height: 280px;"></div>
          </a-card>
        </a-col>
      <a-col :xs="24" :lg="14">
        <a-card size="small" title="任务列表" class="shadow-sm">
          <a-table
            :data-source="tasks"
            row-key="task_id"
            :pagination="{
              current: pagination.page,
              pageSize: pagination.limit,
              total: pagination.total,
              showSizeChanger: true,
            }"
            :loading="loading"
            @change="onTaskTableChange"
          >
            <a-table-column title="task_id" dataIndex="task_id" key="task_id" :width="160" />
            <a-table-column title="type" dataIndex="type" key="type" :width="140" />
            <a-table-column title="status" dataIndex="status" key="status" :width="120">
              <template #default="{ record }">
                <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="trigger" dataIndex="trigger" key="trigger" />
            <a-table-column title="操作" key="action" :width="90">
              <template #default="{ record }">
                <a-button type="link" size="small" @click="viewTask(record.task_id)">查看</a-button>
              </template>
            </a-table-column>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <div ref="detailAnchorRef"></div>
    <a-card size="small" title="任务详情" class="shadow-sm">
      <div v-if="!selectedTask" class="text-sm text-[#57606a] dark:text-[#7d8590]">在任务列表中选择一条任务</div>
      <div v-else class="space-y-3">
        <div class="flex items-center justify-between">
          <div class="text-sm">
            <span class="text-[#57606a] dark:text-[#7d8590]">Task：</span>
            <span class="font-mono">{{ selectedTask.task_id }}</span>
            <a-tag class="ml-2" :color="statusColor(selectedTask.status)">{{ statusLabel(selectedTask.status) }}</a-tag>
          </div>
          <div class="flex items-center gap-2">
            <a-button size="small" @click="fetchLogs(selectedTask.task_id, 5)" :loading="logLoading">刷新日志</a-button>
            <a-button size="small" danger :disabled="!isCancelable" @click="openCancel">取消任务</a-button>
          </div>
        </div>

        <a-row :gutter="16">
          <a-col :xs="24" :lg="10">
            <a-card size="small" title="时间线" :bordered="false">
              <a-timeline>
                <a-timeline-item>
                  排队：{{ selectedTask.queued_at ?? '-' }}
                </a-timeline-item>
                <a-timeline-item v-if="selectedTask.started_at">
                  开始：{{ selectedTask.started_at }}
                </a-timeline-item>
                <a-timeline-item v-if="selectedTask.finished_at">
                  结束：{{ selectedTask.finished_at }}
                </a-timeline-item>
              </a-timeline>
              <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-2">
                耗时：{{ selectedTask.duration_secs ?? '-' }} 秒
              </div>
            </a-card>
          </a-col>
          <a-col :xs="24" :lg="14">
            <a-card size="small" title="参数配置（JSON）" :bordered="false">
              <pre class="text-xs whitespace-pre-wrap break-all bg-gray-50 border rounded p-2">
{{ JSON.stringify(selectedTask.config ?? {}, null, 2) }}
              </pre>
            </a-card>
          </a-col>
        </a-row>

        <a-card size="small" title="最新 5 条日志" :bordered="false">
          <a-list size="small" :data-source="latestLogs" :locale="{ emptyText: logLoading ? '加载中...' : '暂无日志' }">
            <template #renderItem="{ item }">
              <a-list-item>
                <div class="w-full">
                  <div class="flex items-center gap-2 text-xs text-[#57606a] dark:text-[#7d8590]">
                    <span class="font-mono">{{ item.timestamp }}</span>
                    <a-tag :bordered="false" color="blue">{{ String(item.level ?? '').toUpperCase() }}</a-tag>
                  </div>
                  <div class="text-sm">{{ item.message }}</div>
                </div>
              </a-list-item>
            </template>
          </a-list>
          <div class="text-xs text-[#57606a] dark:text-[#7d8590] mt-2" v-if="selectedTask.log_summary">
            摘要：{{ selectedTask.log_summary }}
          </div>
        </a-card>
      </div>
    </a-card>

    <a-modal
      v-model:open="cancelOpen"
      title="取消任务"
      :confirm-loading="cancelLoading"
      ok-text="确认取消"
      cancel-text="返回"
      @ok="submitCancel"
    >
      <div class="text-sm text-gray-600 mb-2">可选填写取消原因（会写入任务日志）</div>
      <a-textarea v-model:value="cancelReason" :auto-size="{ minRows: 3, maxRows: 6 }" placeholder="例如：误触发 / 参数有误 / 中期汇报演示结束" />
    </a-modal>
  </div>
</template>
