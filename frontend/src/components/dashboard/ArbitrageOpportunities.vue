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
  buy_platform: string;
  sell_platform: string;
  buy_price: number;
  sell_price: number;
  profit_usdt: number;
}

interface PaginationData {
  total: number;
  page: number;
  limit: number;
}

const props = defineProps<Props>();

const currentPage = ref(1);
const itemsPerPage = 10;
const sortField = ref<SortField>('netProfit');
const sortDirection = ref<SortDirection>('desc');
const opportunities = ref<ApiOpportunity[]>([]);
const pagination = ref<PaginationData>({ total: 0, page: 1, limit: itemsPerPage });
const isLoading = ref(false);
const errorMessage = ref('');
const unsupportedNotice = ref('');

const sortFieldMapping: Record<SortField, string | null> = {
  timestamp: null,
  grossProfit: null,
  netProfit: 'profit_usdt',
};

const isDark = computed(() => props.theme === 'dark');

const stats = computed(() => {
  const profits = opportunities.value.map((item) => item.profit_usdt ?? 0);
  const total = pagination.value.total;
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

const fetchOpportunities = async () => {
  isLoading.value = true;
  errorMessage.value = '';

  try {
    const { data } = await api.getOpportunities({
      page: currentPage.value,
      limit: itemsPerPage,
      sort_by: sortFieldMapping[sortField.value] ?? undefined,
      order: sortDirection.value,
    });
    const payload = data?.data;
    opportunities.value = payload?.items ?? [];
    pagination.value = payload?.pagination ?? {
      total: opportunities.value.length,
      page: currentPage.value,
      limit: itemsPerPage,
    };
  } catch (error: any) {
    console.error(error);
    errorMessage.value =
      error?.message ?? error?.data?.message ?? '套利机会列表获取失败';
    opportunities.value = [];
    pagination.value = { total: 0, page: 1, limit: itemsPerPage };
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchOpportunities);

watch([currentPage, sortField, sortDirection], () => {
  fetchOpportunities();
});

const handleSort = (field: SortField) => {
  unsupportedNotice.value = '';
  if (!sortFieldMapping[field]) {
    unsupportedNotice.value = '后端暂未提供该字段，无法排序。';
    return;
  }

  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortField.value = field;
    sortDirection.value = 'desc';
  }
};

const goToPage = (page: number) => {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value);
};

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(pagination.value.total / itemsPerPage));
});

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

const formatCurrency = (value: number) => `$${value.toFixed(2)}`;
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
            <tr v-if="isLoading">
              <td colspan="6" class="px-4 py-6 text-center">
                <Loader2 class="w-4 h-4 inline-block animate-spin mr-2 text-[#58a6ff]" />
                <span :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">加载中...</span>
              </td>
            </tr>
            <tr
              v-else-if="!opportunities.length"
              :class="['border-b', isDark ? 'border-[#21262d]' : 'border-[#d0d7de]']"
            >
              <td colspan="6" class="px-4 py-6 text-center text-sm" :class="isDark ? 'text-[#7d8590]' : 'text-[#57606a]'">
                暂无数据，确认后端是否已生成套利机会。
              </td>
            </tr>
            <tr
              v-else
              v-for="opportunity in opportunities"
              :key="opportunity.id"
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
            Showing
            {{
              Math.min((currentPage - 1) * itemsPerPage + 1, pagination.total === 0 ? 0 : pagination.total)
            }}-
            {{ Math.min(currentPage * itemsPerPage, pagination.total) }}
            of {{ pagination.total }}
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
            :disabled="currentPage === 1"
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
            :disabled="currentPage === totalPages"
            @click="goToPage(currentPage + 1)"
          >
            <ChevronRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
