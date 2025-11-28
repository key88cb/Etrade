<script setup lang="ts">
import { ref } from 'vue';
import api from '../api';

interface TimelineItem {
  task_id: string;
  type: string;
  status: string;
  trigger: string;
  started_at?: string;
}

const date = ref<string>(new Date().toISOString().slice(0, 10));
const loading = ref(false);
const items = ref<TimelineItem[]>([]);
const errorMessage = ref('');

const fetchTimeline = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getTasks();
    const all = data?.data?.items ?? [];
    items.value = all.filter((item: TimelineItem) =>
      item.started_at?.startsWith(date.value),
    );
  } catch (error: any) {
    errorMessage.value = error?.message ?? '历史记录获取失败';
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="p-6 lg:p-8 space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">历史回放</h1>
        <p class="text-sm text-gray-500">按日期查看任务链路</p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="date"
          type="date"
          class="border rounded px-3 py-2 text-sm"
        />
        <button
          type="button"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded"
          :disabled="loading"
          @click="fetchTimeline"
        >
          查询
        </button>
      </div>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>

    <div class="bg-white rounded-lg shadow border p-4 space-y-4">
      <div v-if="items.length === 0" class="text-gray-500 text-sm">
        请选择日期后点击查询，以查看任务回放。
      </div>
      <div v-else class="space-y-4">
        <div
          v-for="task in items"
          :key="task.task_id"
          class="flex items-center gap-4"
        >
          <div class="w-32 text-xs text-gray-500">
            {{ task.started_at ?? '未开始' }}
          </div>
          <div class="flex-1 border-l pl-4">
            <div class="text-sm font-medium">{{ task.type }}</div>
            <div class="text-xs text-gray-500">
              状态：{{ task.status }} · 触发：{{ task.trigger || 'N/A' }}
            </div>
            <div class="text-xs text-gray-400">Task ID: {{ task.task_id }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
