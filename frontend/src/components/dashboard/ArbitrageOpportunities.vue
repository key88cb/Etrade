<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import {
  TrendingUp,
  DollarSign,
  Activity,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from 'lucide-vue-next';
import api from '../../api';

type Theme = 'light' | 'dark';
type SortField = 'timestamp' | 'netProfit' | 'grossProfit';
type SortDirection = 'asc' | 'desc';

interface Props {
  theme: Theme;
}

interface ApiOpportunity {
  id: number;
  batch_id?: number;
  buy_platform: string;
  sell_platform: string;
  buy_price: number;
  sell_price: number;
  profit_usdt: number;
}

interface Batch {
  id: number;
  name: string;
  description?: string;
  last_refreshed_at?: string;
}

const props = defineProps<Props>();

const itemsPerPage = 10;
const currentPage = ref(1);
const sortField = ref<SortField>('netProfit');
const sortDirection = ref<SortDirection>('desc');
const opportunities = ref<ApiOpportunity[]>([]);
const opportunitiesLoaded = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');
const unsupportedNotice = ref('');
const batches = ref<Batch[]>([]);
const batchesLoading = ref(false);
const batchError = ref('');
const openedBatchIds = ref<number[]>([]);

const isDark = computed(() => props.theme === 'dark');

const filteredOpportunities = computed(() => {
  if (!openedBatchIds.value.length) return [];
  return opportunities.value.filter(
    (item) => typeof item.batch_id === 'number' && openedBatchIds.value.includes(item.batch_id),
  );
});

const sortedFilteredOpportunities = computed(() => {
  const list = [...filteredOpportunities.value];
  if (sortField.value === 'netProfit') {
    list.sort((a, b) => {
      const diff = (a.profit_usdt ?? 0) - (b.profit_usdt ?? 0);
      return sortDirection.value === 'asc' ? diff : -diff;
    });
  }
  return list;
});

const paginatedOpportunities = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return sortedFilteredOpportunities.value.slice(start, start + itemsPerPage);
});

const filteredTotal = computed(() => sortedFilteredOpportunities.value.length);

const totalPages = computed(() => {
  if (!filteredTotal.value) {
    return 1;
  }
  return Math.max(1, Math.ceil(filteredTotal.value / itemsPerPage));
});

const stats = computed(() => {
  const profits = filteredOpportunities.value.map((item) => item.profit_usdt ?? 0);
  const total = filteredTotal.value;
  const maxProfit = profits.length ? Math.max(...profits) : 0;
  const totalProfit = profits.reduce((sum, value) => sum + value, 0);
  const avgProfit = profits.length ? totalProfit / profits.length : 0;

  return {
    totalOpportunities: total,
    maxProfit,
    avgProfit,
    totalPotentialProfit: totalProfit,
  };
});

const fetchBatches = async () => {
  batchesLoading.value = true;
  batchError.value = '';
  try {
    const { data } = await api.getBatches();
    batches.value = data?.data ?? data ?? [];
  } catch (error: any) {
    batchError.value = error?.message ?? '批次列表获取失败';
  } finally {
    batchesLoading.value = false;
  }
};

const fetchAllOpportunities = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const aggregated: ApiOpportunity[] = [];
    const pageSize = 200;
    let page = 1;
    let total = Number.POSITIVE_INFINITY;

    while (aggregated.length < total) {
      const { data } = await api.getOpportunities({
        page,
        limit: pageSize,
        sort_by: 'profit_usdt',
        order: 'desc',
      });
      const payload = data?.data;
      const items: ApiOpportunity[] = payload?.items ?? [];
      const pagination = payload?.pagination;
      if (pagination?.total) {
        total = pagination.total;
      }
      aggregated.push(...items);
      if (!items.length || aggregated.length >= total) {
        break;
      }
      page += 1;
    }
    opportunities.value = aggregated;
    opportunitiesLoaded.value = true;
  } catch (error: any) {
    errorMessage.value = error?.message ?? '套利机会列表获取失败';
  } finally {
    isLoading.value = false;
  }
};

const ensureOpportunitiesLoaded = async () => {
  if (opportunitiesLoaded.value || isLoading.value) return;
  await fetchAllOpportunities();
};

const isBatchOpened = (id: number) => openedBatchIds.value.includes(id);

const toggleBatch = async (batchId: number) => {
  if (isBatchOpened(batchId)) {
    openedBatchIds.value = openedBatchIds.value.filter((id) => id !== batchId);
    return;
  }
  await ensureOpportunitiesLoaded();
  openedBatchIds.value = [...openedBatchIds.value, batchId];
};

const openedBatches = computed(() =>
  batches.value.filter((batch) => openedBatchIds.value.includes(batch.id)),
);

const handleSort = (field: SortField) => {
  unsupportedNotice.value = '';
  if (field !== 'netProfit') {
    unsupportedNotice.value = '暂不支持该排序字段';
    return;
  }
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
};

const goToPage = (page: number) => {
  const capped = Math.min(Math.max(page, 1), totalPages.value);
  currentPage.value = capped;
};

const paginationRange = computed(() => {
  const pages = totalPages.value;
  if (pages <= 5) {
    return Array.from({ length: pages }, (_, i) => i + 1);
  }

  if (currentPage.value <= 3) {
    return [1, 2, 3, 4, 5];
  }

  if (currentPage.value >= pages - 2) {
    return [pages - 4, pages - 3, pages - 2, pages - 1, pages];
  }

  return [
    currentPage.value - 2,
    currentPage.value - 1,
    currentPage.value,
    currentPage.value + 1,
    currentPage.value + 2,
  ];
});

const showingRange = computed(() => {
  if (!filteredTotal.value) {
    return { start: 0, end: 0 };
  }
  const start = (currentPage.value - 1) * itemsPerPage + 1;
  const end = Math.min(currentPage.value * itemsPerPage, filteredTotal.value);
  return { start, end };
});

const formatCurrency = (value: number) => `$${value.toFixed(2)}`;

onMounted(() => {
  fetchBatches();
});

watch(filteredOpportunities, () => {
  currentPage.value = 1;
});

watch(
  () => totalPages.value,
  (pages) => {
    if (currentPage.value > pages) {
      currentPage.value = pages;
    }
  },
);
</script>

<template>
  <div class="space-y-4">
    <div
      class="rounded-md border p-4"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div class="flex items-start justify-between mb-3">
        <div>
          <h3 class="text-sm font-semibold" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">批次筛选</h3>
          <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
            先选择一个或多个批次后再加载套利机会，可以随时关闭批次以清空视图。
          </p>
        </div>
        <button
          type="button"
          class="text-xs px-3 py-1 rounded border"
          :class="
            isDark
              ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff]'
              : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da]'
          "
          @click="fetchBatches"
          :disabled="batchesLoading"
        >
          {{ batchesLoading ? '加载中...' : '刷新批次' }}
        </button>
      </div>
      <p v-if="batchError" class="text-xs text-[#f85149] mb-2">{{ batchError }}</p>
      <div class="flex flex-wrap gap-2 mb-3" v-if="batches.length">
        <button
          v-for="batch in batches"
          :key="batch.id"
          type="button"
          class="px-3 py-1 rounded text-xs border transition-colors"
          :class="
            isBatchOpened(batch.id)
              ? 'bg-[#1f6feb] border-[#1f6feb] text-white'
              : isDark
                ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff]'
                : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da]'
          "
          @click="toggleBatch(batch.id)"
        >
          {{ batch.name }} (#{{ batch.id }})
        </button>
      </div>
      <p v-else-if="!batchesLoading" class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
        暂无批次，先通过数据管理页面创建。
      </p>
      <div v-if="openedBatches.length" class="flex flex-wrap gap-2 text-xs">
        <span :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">已打开批次：</span>
        <button
          v-for="batch in openedBatches"
          :key="`opened-${batch.id}`"
          type="button"
          class="px-2 py-1 rounded-full border flex items-center gap-1"
          :class="isDark ? 'border-[#30363d] text-[#e6edf3]' : 'border-[#d0d7de] text-[#24292f]'"
          @click="toggleBatch(batch.id)"
        >
          {{ batch.name }} (#{{ batch.id }})
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
            class="w-3 h-3"
            fill="none"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <p v-else class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
        暂未选择批次。
      </p>
    </div>

    <div
      v-if="openedBatchIds.length"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
    >
      <div
        class="rounded-md border p-4"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
            Total Opportunities
          </span>
          <Activity class="w-4 h-4 text-[#58a6ff]" />
        </div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
          {{ stats.totalOpportunities }}
        </div>
        <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
          detected arbitrage chances
        </p>
      </div>

      <div
        class="rounded-md border p-4"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
            Max Profit
          </span>
          <TrendingUp class="w-4 h-4 text-[#3fb950]" />
        </div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
          ${{ stats.maxProfit.toFixed(2) }}
        </div>
        <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
          highest net profit
        </p>
      </div>

      <div
        class="rounded-md border p-4"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
            Average Profit
          </span>
          <DollarSign class="w-4 h-4 text-[#d29922]" />
        </div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
          ${{ stats.avgProfit.toFixed(2) }}
        </div>
        <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
          average net profit
        </p>
      </div>

      <div
        class="rounded-md border p-4"
        :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
            Total Potential
          </span>
          <TrendingUp class="w-4 h-4 text-[#bc8cff]" />
        </div>
        <div class="mb-1" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
          ${{ stats.totalPotentialProfit.toFixed(2) }}
        </div>
        <p class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
          cumulative profit
        </p>
      </div>
    </div>

    <div
      class="rounded-md border overflow-hidden"
      :class="isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'"
    >
      <div v-if="errorMessage" class="px-4 py-3 text-sm text-[#f85149] border-b border-[#30363d]">
        {{ errorMessage }}
      </div>
      <div
        v-else-if="unsupportedNotice"
        class="px-4 py-2 text-xs"
        :class="isDark ? 'text-[#d29922] border-b border-[#30363d]' : 'text-[#bf8700] border-b border-[#d0d7de]'"
      >
        {{ unsupportedNotice }}
      </div>
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead :class="isDark ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]'">
            <tr :class="isDark ? 'border-b border-[#30363d]' : 'border-b border-[#d0d7de]'">
              <th class="px-4 py-3 text-left text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                ID
              </th>
              <th class="px-4 py-3 text-left text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Buy Platform
              </th>
              <th class="px-4 py-3 text-left text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Sell Platform
              </th>
              <th class="px-4 py-3 text-right text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Buy Price
              </th>
              <th class="px-4 py-3 text-right text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                Sell Price
              </th>
              <th
                class="px-4 py-3 text-right text-xs cursor-pointer"
                :class="isDark ? 'text-[#7d8590] hover:text-[#58a6ff]' : 'text-[#57606a] hover:text-[#0969da]'"
                @click="handleSort('netProfit')"
              >
                <span class="flex items-center justify-end gap-1">
                  Net Profit
                  <svg
                    class="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="m8 7 4-4 4 4m0 10-4 4-4-4" />
                  </svg>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!openedBatchIds.length">
              <td colspan="6" class="px-4 py-6 text-center text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                请选择左侧批次以查看套利数据。
              </td>
            </tr>
            <tr v-else-if="isLoading">
              <td colspan="6" class="px-4 py-6 text-center">
                <Loader2 class="w-4 h-4 inline-block animate-spin mr-2 text-[#58a6ff]" />
                <span :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">加载中...</span>
              </td>
            </tr>
            <tr
              v-else-if="!filteredTotal"
              :class="['border-b', isDark ? 'border-[#21262d]' : 'border-[#d0d7de]']"
            >
              <td colspan="6" class="px-4 py-6 text-center text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                所选批次暂未生成套利机会。
              </td>
            </tr>
            <tr
              v-else
              v-for="opportunity in paginatedOpportunities"
              :key="`${opportunity.batch_id}-${opportunity.id}`"
              :class="[
                'border-b transition-colors',
                isDark ? 'border-[#21262d] hover:bg-[#0d1117]' : 'border-[#d0d7de] hover:bg-[#f6f8fa]',
              ]"
            >
              <td class="px-4 py-3 text-sm" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                {{ opportunity.id }}
              </td>
              <td class="px-4 py-3 text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                {{ opportunity.buy_platform || '--' }}
              </td>
              <td class="px-4 py-3 text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                {{ opportunity.sell_platform || '--' }}
              </td>
              <td class="px-4 py-3 text-sm text-right" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                {{ formatCurrency(opportunity.buy_price ?? 0) }}
              </td>
              <td class="px-4 py-3 text-sm text-right" :class="isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'">
                {{ formatCurrency(opportunity.sell_price ?? 0) }}
              </td>
              <td class="px-4 py-3 text-sm text-right text-[#3fb950]">
                {{ formatCurrency(opportunity.profit_usdt ?? 0) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        class="px-4 py-3 border-t flex items-center justify-between"
        :class="isDark ? 'border-[#30363d] bg-[#0d1117]' : 'border-[#d0d7de] bg-[#f6f8fa]'"
      >
          <div class="text-xs" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
            Showing {{ showingRange.start }}-{{ showingRange.end }} of {{ filteredTotal }}
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="p-1.5 border rounded text-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            :class="
              isDark
                ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff]'
                : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da]'
            "
            :disabled="currentPage === 1 || !filteredTotal"
            @click="goToPage(currentPage - 1)"
          >
            <ChevronLeft class="w-4 h-4" />
          </button>

            <button
              v-for="page in paginationRange"
              :key="page"
              type="button"
              class="px-3 py-1 rounded text-sm"
              :class="
                currentPage === page
                  ? 'bg-[#1f6feb] text-white'
                  : isDark
                    ? 'border border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff]'
                    : 'border border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da]'
              "
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            <button
              type="button"
              class="p-1.5 border rounded text-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              :class="
                isDark
                ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff]'
                : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da]'
            "
              :disabled="currentPage === totalPages || !filteredTotal"
            @click="goToPage(currentPage + 1)"
          >
            <ChevronRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
