<script setup lang="ts">
import { onMounted, ref } from 'vue';
import api from '../api';

interface BatchItem {
  id: number;
  name: string;
  description?: string;
  last_refreshed_at?: string;
  created_at?: string;
}

const batches = ref<BatchItem[]>([]);
const loading = ref(false);
const formVisible = ref(false);
const form = ref<{ name: string; description: string }>({ name: '', description: '' });
const selectedBatch = ref<BatchItem | null>(null);
const errorMessage = ref('');

const fetchBatches = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getBatches();
    batches.value = data?.data ?? data ?? [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '批次列表获取失败';
  } finally {
    loading.value = false;
  }
};

const openCreate = () => {
  form.value = { name: '', description: '' };
  formVisible.value = true;
};

const createBatch = async () => {
  try {
    await api.createBatch(form.value);
    formVisible.value = false;
    await fetchBatches();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '创建批次失败';
  }
};

const refreshBatch = async (batch: BatchItem) => {
  if (!confirm('刷新批次会更新最后时间，确认操作？')) return;
  try {
    await api.updateBatch(batch.id, { name: batch.name, description: batch.description, refreshed: true });
    await fetchBatches();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '刷新失败';
  }
};

onMounted(fetchBatches);
</script>

<template>
  <div class="p-6 lg:p-8 space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">批次管理</h1>
        <p class="text-sm text-gray-500">查看批次信息并快速刷新。</p>
      </div>
      <button type="button" class="px-4 py-2 bg-indigo-600 text-white rounded text-sm" @click="openCreate">
        新建批次
      </button>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>

    <div class="bg-white rounded-lg shadow border divide-y divide-gray-200">
      <div
        v-for="batch in batches"
        :key="batch.id"
        class="p-4 flex items-center justify-between gap-4"
      >
        <div class="space-y-1">
          <div class="text-base font-medium">
            {{ batch.name }}
            <span class="text-xs text-gray-400 ml-2">ID: {{ batch.id }}</span>
          </div>
          <div class="text-sm text-gray-600">{{ batch.description || '暂无描述' }}</div>
          <div class="text-xs text-gray-500">
            最近刷新：{{ batch.last_refreshed_at ?? '尚未刷新' }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="text-blue-600 text-xs hover:underline"
            @click="selectedBatch = batch"
          >
            查看
          </button>
          <button
            class="text-green-600 text-xs hover:underline"
            @click="refreshBatch(batch)"
          >
            刷新
          </button>
        </div>
      </div>
      <div v-if="!loading && batches.length === 0" class="p-6 text-center text-gray-500 text-sm">
        暂无批次数据
      </div>
    </div>

    <div v-if="selectedBatch" class="bg-white rounded-lg shadow border p-4 space-y-2">
      <h2 class="text-lg font-semibold">批次详情</h2>
      <div class="text-sm text-gray-700">名称：{{ selectedBatch.name }}</div>
      <div class="text-sm text-gray-700">描述：{{ selectedBatch.description || '-' }}</div>
      <div class="text-sm text-gray-700">
        最近刷新：{{ selectedBatch.last_refreshed_at ?? '尚未刷新' }}
      </div>
    </div>

    <div
      v-if="formVisible"
      class="fixed inset-0 bg-black/30 flex items-center justify-center z-10"
      @click.self="formVisible = false"
    >
      <div class="bg-white rounded-lg shadow-lg w-full max-w-md p-6 space-y-4">
        <h2 class="text-lg font-semibold">新建批次</h2>
        <div class="space-y-2">
          <label class="text-sm text-gray-600">名称</label>
          <input v-model="form.name" type="text" class="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div class="space-y-2">
          <label class="text-sm text-gray-600">描述</label>
          <textarea
            v-model="form.description"
            rows="3"
            class="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div class="flex justify-end gap-3">
          <button type="button" class="px-4 py-2 text-sm text-gray-600" @click="formVisible = false">
            取消
          </button>
          <button type="button" class="px-4 py-2 bg-blue-600 text-white text-sm rounded" @click="createBatch">
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
