<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import api, { type TemplatePayload } from '../api';

interface TemplateItem {
  id: number;
  name: string;
  task_type: string;
  config: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

const templates = ref<TemplateItem[]>([]);
const loading = ref(false);
const formVisible = ref(false);
const editId = ref<number | null>(null);
const runMessage = ref('');
const form = reactive<TemplatePayload>({
  name: '',
  task_type: 'collect_binance',
  config: {},
});
const errorMessage = ref('');

const resetForm = () => {
  form.name = '';
  form.task_type = 'collect_binance';
  form.config = {};
  editId.value = null;
};

const fetchTemplates = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const { data } = await api.getTemplates();
    templates.value = data?.data ?? data ?? [];
  } catch (error: any) {
    errorMessage.value = error?.message ?? '模板列表获取失败';
  } finally {
    loading.value = false;
  }
};

const openCreate = () => {
  resetForm();
  formVisible.value = true;
};

const submitForm = async () => {
  try {
    if (!form.name) {
      errorMessage.value = '请填写模板名称';
      return;
    }
    if (editId.value) {
      await api.updateTemplate(editId.value, form);
    } else {
      await api.createTemplate(form);
    }
    formVisible.value = false;
    runMessage.value = '';
    await fetchTemplates();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '模板保存失败';
  }
};

const editTemplate = (template: TemplateItem) => {
  editId.value = template.id;
  form.name = template.name;
  form.task_type = template.task_type;
  form.config = { ...template.config };
  formVisible.value = true;
};

const deleteTemplate = async (id: number) => {
  if (!confirm('确定删除该模板？')) return;
  try {
    await api.deleteTemplate(id);
    await fetchTemplates();
  } catch (error: any) {
    errorMessage.value = error?.message ?? '删除失败';
  }
};

const runTemplate = async (id: number) => {
  try {
    runMessage.value = '正在运行模板...';
    const { data } = await api.runTemplate(id);
    const taskId = data?.data?.task_id ?? data?.task_id;
    runMessage.value = `模板已触发任务：${taskId}`;
  } catch (error: any) {
    runMessage.value = error?.message ?? '运行模板失败';
  }
};

const formattedConfig = computed(() => JSON.stringify(form.config, null, 2));

const handleConfigChange = (event: Event) => {
  const value = (event.target as HTMLTextAreaElement).value;
  try {
    form.config = value ? JSON.parse(value) : {};
    errorMessage.value = '';
  } catch (error) {
    errorMessage.value = '配置必须为合法 JSON';
  }
};

onMounted(fetchTemplates);
</script>

<template>
  <div class="p-6 lg:p-8 space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">模板管理</h1>
        <p class="text-sm text-gray-500">维护任务参数模板，支持一键运行。</p>
      </div>
      <button
        type="button"
        class="px-4 py-2 rounded bg-blue-600 text-white text-sm"
        @click="openCreate"
      >
        新建模板
      </button>
    </header>

    <div v-if="errorMessage" class="bg-red-50 text-red-600 text-sm rounded p-3">
      {{ errorMessage }}
    </div>
    <div v-if="runMessage" class="bg-blue-50 text-blue-700 text-sm rounded p-3">
      {{ runMessage }}
    </div>

    <div class="bg-white rounded-lg shadow border">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th class="px-4 py-2 text-left">名称</th>
              <th class="px-4 py-2 text-left">任务类型</th>
              <th class="px-4 py-2 text-left">更新</th>
              <th class="px-4 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="item in templates" :key="item.id">
              <td class="px-4 py-2">{{ item.name }}</td>
              <td class="px-4 py-2 font-mono text-xs">{{ item.task_type }}</td>
              <td class="px-4 py-2 text-xs text-gray-500">{{ item.updated_at ?? '-' }}</td>
              <td class="px-4 py-2 text-right space-x-2">
                <button class="text-blue-600 hover:underline text-xs" @click="editTemplate(item)">
                  编辑
                </button>
                <button class="text-green-600 hover:underline text-xs" @click="runTemplate(item.id)">
                  运行
                </button>
                <button class="text-red-600 hover:underline text-xs" @click="deleteTemplate(item.id)">
                  删除
                </button>
              </td>
            </tr>
            <tr v-if="!loading && templates.length === 0">
              <td colspan="4" class="px-4 py-6 text-center text-gray-500">暂无模板</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="formVisible"
      class="fixed inset-0 bg-black/30 flex items-center justify-center z-10"
      @click.self="formVisible = false"
    >
      <div class="bg-white rounded-lg shadow-lg w-full max-w-lg p-6 space-y-4">
        <h2 class="text-lg font-semibold">
          {{ editId ? '编辑模板' : '新建模板' }}
        </h2>
        <div class="space-y-2">
          <label class="text-sm text-gray-600">名称</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div class="space-y-2">
          <label class="text-sm text-gray-600">任务类型</label>
          <select
            v-model="form.task_type"
            class="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="collect_binance">collect_binance</option>
            <option value="collect_uniswap">collect_uniswap</option>
            <option value="process_prices">process_prices</option>
            <option value="analyse">analyse</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="text-sm text-gray-600">配置（JSON）</label>
          <textarea
            :value="formattedConfig"
            @input="handleConfigChange"
            rows="6"
            class="w-full border rounded px-3 py-2 text-xs font-mono"
          />
          <p class="text-xs text-gray-500">
            根据任务类型填写对应字段，例如 collect_binance 需要 csv_path、import_percentage 等。
          </p>
        </div>
        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-gray-600"
            @click="formVisible = false"
          >
            取消
          </button>
          <button
            type="button"
            class="px-4 py-2 bg-blue-600 text-white text-sm rounded"
            @click="submitForm"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
