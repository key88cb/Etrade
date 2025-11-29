<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
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

interface TaskDetail {
  task_id: string;
  type: string;
  status: string;
  trigger: string;
  config: Record<string, unknown>;
  queued_at?: string;
  started_at?: string;
  finished_at?: string;
  log_summary?: string;
  duration_secs?: number;
}

const tasks = ref<TaskItem[]>([]);
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0,
});
const loading = ref(false);
const selectedTask = ref<TaskDetail | null>(null);
const taskLogs = ref<Array<{ timestamp: string; level: string; message: string }>>([]);
const logLoading = ref(false);
const errorMessage = ref('');

const fetchTasks = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getTasks({ page: pagination.page, limit: pagination.limit });
    tasks.value = data.data?.items ?? [];
    const pager = data.data?.pagination;
    if (pager) {
      pagination.total = pager.total ?? 0;
      pagination.page = pager.page ?? pagination.page;
      pagination.limit = pager.limit ?? pagination.limit;
    }
  } catch (error: any) {
    errorMessage.value = error?.message ?? '任务列表获取失败';
  } finally {
    loading.value = false;
  }
};

const viewTask = async (taskId: string) => {
  selectedTask.value = null;
  taskLogs.value = [];
  try {
    const { data } = await api.getTaskDetail(taskId);
    selectedTask.value = data?.data ?? data;
    await fetchLogs(taskId);
  } catch (error: any) {
    errorMessage.value = error?.message ?? '任务详情获取失败';
  }
};

const fetchLogs = async (taskId: string) => {
  logLoading.value = true;
  try {
    const { data } = await api.getTaskLogs(taskId);
    taskLogs.value = data?.data?.items ?? data?.items ?? [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '任务日志获取失败';
  } finally {
    logLoading.value = false;
  }
};

onMounted(fetchTasks);
</script>

<template>
  <div class="p-6 lg:p-8 space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">任务中心</h1>
        <p class="text-sm text-gray-500">查看任务状态、参数与运行日志</p>
      </div>
      <button
        type="button"
        class="px-4 py-2 rounded bg-blue-600 text-white text-sm"
        :disabled="loading"
        @click="fetchTasks"
      >
        刷新
      </button>
    </header>

    <div v-if="errorMessage" class="rounded-md bg-red-50 p-3 text-sm text-red-600">
      {{ errorMessage }}
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-white rounded-lg shadow border">
        <div class="p-4 border-b flex items-center justify-between">
          <h2 class="text-base font-medium">任务列表</h2>
          <span class="text-xs text-gray-500">{{ tasks.length }} / {{ pagination.total }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th class="px-4 py-2 text-left">Task ID</th>
                <th class="px-4 py-2 text-left">类型</th>
                <th class="px-4 py-2 text-left">状态</th>
                <th class="px-4 py-2 text-left">触发</th>
                <th class="px-4 py-2" />
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 text-sm">
              <tr v-for="task in tasks" :key="task.task_id">
                <td class="px-4 py-2">{{ task.task_id }}</td>
                <td class="px-4 py-2">{{ task.type }}</td>
                <td class="px-4 py-2">{{ task.status }}</td>
                <td class="px-4 py-2">{{ task.trigger || 'N/A' }}</td>
                <td class="px-4 py-2 text-right">
                  <button
                    type="button"
                    class="text-blue-600 hover:underline text-xs"
                    @click="viewTask(task.task_id)"
                  >
                    查看
                  </button>
                </td>
              </tr>
              <tr v-if="!loading && tasks.length === 0">
                <td colspan="5" class="px-4 py-6 text-center text-gray-500">暂无任务</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="p-4 border-t flex items-center gap-2 text-xs text-gray-600">
          <span>共 {{ pagination.total }} 条</span>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow border min-h-[320px]">
        <div class="p-4 border-b">
          <h2 class="text-base font-medium">任务详情</h2>
          <p class="text-xs text-gray-500">选择一个任务以查看配置和日志</p>
        </div>
        <div class="p-4 space-y-4 text-sm">
          <div v-if="!selectedTask" class="text-gray-500">请在任务列表中选择一条任务</div>
          <div v-else>
            <div class="flex flex-col gap-1">
              <div><span class="text-gray-500">Task ID：</span>{{ selectedTask.task_id }}</div>
              <div><span class="text-gray-500">类型：</span>{{ selectedTask.type }}</div>
              <div><span class="text-gray-500">状态：</span>{{ selectedTask.status }}</div>
              <div><span class="text-gray-500">触发：</span>{{ selectedTask.trigger || 'N/A' }}</div>
              <div><span class="text-gray-500">耗时：</span>{{ selectedTask.duration_secs ?? '-' }} 秒</div>
            </div>
            <div class="border rounded p-3 bg-gray-50">
              <div class="text-xs text-gray-500 mb-2">参数配置</div>
              <pre class="text-xs whitespace-pre-wrap break-all">
{{ JSON.stringify(selectedTask.config ?? {}, null, 2) }}
              </pre>
            </div>
            <div>
              <div class="text-xs text-gray-500 mb-2 flex items-center justify-between">
                <span>任务日志</span>
                <button
                  type="button"
                  class="text-blue-600 hover:underline"
                  :disabled="logLoading"
                  @click="selectedTask && fetchLogs(selectedTask.task_id)"
                >
                  刷新
                </button>
              </div>
              <div class="border rounded max-h-48 overflow-y-auto bg-gray-50 text-xs space-y-2 p-2">
                <div v-if="logLoading" class="text-gray-500">加载日志...</div>
                <div v-else-if="taskLogs.length === 0" class="text-gray-400">暂无日志</div>
                <div v-for="log in taskLogs" :key="log.timestamp + log.message" class="font-mono">
                  <span class="text-gray-500">{{ log.timestamp }}</span>
                  <span class="ml-2 uppercase text-gray-600">{{ log.level }}</span>
                  <span class="ml-2">{{ log.message }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
