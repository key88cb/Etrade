import axios from 'axios';

// 允许通过 VITE_BACKEND_URL 自定义后端地址，默认指向本地开发环境
export const backendURL =
  import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8888/api/v1';

const instance = axios.create({
  baseURL: backendURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

instance.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error.response?.data ?? error),
);

interface OpportunitiesParams {
  page?: number;
  limit?: number;
  sort_by?: string;
  order?: 'asc' | 'desc';
}

interface PriceComparisonParams {
  startTime: number;
  endTime: number;
}

const api = {
  getOpportunities: (params?: OpportunitiesParams) =>
    instance.get('/opportunities', { params }),
  getPriceComparisonData: (params: PriceComparisonParams) =>
    instance.get('/price-comparison', { params }),
};

export default api;
