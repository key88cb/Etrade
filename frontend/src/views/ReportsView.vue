<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import api, { type ReportPayload } from '../api';

interface ReportItem {
  id: number;
  batch_id: number;
  template_id?: number;
  format: string;
  file_path?: string;
  generated_at?: string;
}

const reports = ref<ReportItem[]>([]);
const loading = ref(false);
const errorMessage = ref('');
const form = reactive<ReportPayload>({
  batch_id: 1,
  template_id: undefined,
  format: 'PDF',
  file_path: '',
});
const creating = ref(false);

const fetchReports = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getReports();
    reports.value = data?.data ?? data ?? [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '报告列表获取失败';
  } finally {
    loading.value = false;
  }
};

const submitReport = async () => {
  creating.value = true;
  errorMessage.value = '';
  try {
    await api.createReport(form);
    await fetchReports();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '生成报告失败';
  } finally {
    creating.value = false;
  }
};

onMounted(fetchReports);
</script>

<template>
  <div class="p-6 lg:p-8 space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-gray-900">报告中心</h1>
      <p class="text-sm text-gray-500">生成与查看批次报告。</p>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>

    <section class="bg-white rounded-lg shadow border p-4 space-y-4">
      <h2 class="text-lg font-medium">生成报告</h2>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <label class="text-sm text-gray-600">
          批次 ID
          <input
            v-model.number="form.batch_id"
            type="number"
            min="1"
            class="w-full border rounded px-3 py-2 text-sm mt-1"
          />
        </label>
        <label class="text-sm text-gray-600">
          模板 ID（可选）
          <input
            v-model.number="form.template_id"
            type="number"
            min="1"
            class="w-full border rounded px-3 py-2 text-sm mt-1"
          />
        </label>
        <label class="text-sm text-gray-600">
          格式
          <select v-model="form.format" class="w-full border rounded px-3 py-2 text-sm mt-1">
            <option value="PDF">PDF</option>
            <option value="HTML">HTML</option>
            <option value="Markdown">Markdown</option>
          </select>
        </label>
        <label class="text-sm text-gray-600">
          文件路径（可选）
          <input
            v-model="form.file_path"
            type="text"
            class="w-full border rounded px-3 py-2 text-sm mt-1"
          />
        </label>
      </div>
      <button
        type="button"
        class="px-4 py-2 bg-blue-600 text-white text-sm rounded"
        :disabled="creating"
        @click="submitReport"
      >
        {{ creating ? '生成中...' : '生成报告' }}
      </button>
    </section>

    <section class="bg-white rounded-lg shadow border">
      <div class="p-4 border-b flex items-center justify-between">
        <h2 class="text-lg font-medium">报告列表</h2>
        <button
          type="button"
          class="text-sm text-blue-600 hover:underline"
          :disabled="loading"
          @click="fetchReports"
        >
          刷新
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th class="px-4 py-2 text-left">ID</th>
              <th class="px-4 py-2 text-left">批次</th>
              <th class="px-4 py-2 text-left">模板</th>
              <th class="px-4 py-2 text-left">格式</th>
              <th class="px-4 py-2 text-left">生成时间</th>
              <th class="px-4 py-2 text-left">文件</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="report in reports" :key="report.id">
              <td class="px-4 py-2">{{ report.id }}</td>
              <td class="px-4 py-2">{{ report.batch_id }}</td>
              <td class="px-4 py-2">{{ report.template_id ?? '-' }}</td>
              <td class="px-4 py-2">{{ report.format }}</td>
              <td class="px-4 py-2">{{ report.generated_at ?? '-' }}</td>
              <td class="px-4 py-2">
                <a
                  v-if="report.file_path"
                  :href="report.file_path"
                  target="_blank"
                  class="text-blue-600 text-xs hover:underline"
                >
                  下载
                </a>
                <span v-else class="text-gray-400 text-xs">—</span>
              </td>
            </tr>
            <tr v-if="!loading && reports.length === 0">
              <td colspan="6" class="px-4 py-6 text-center text-gray-500">暂无报告</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
