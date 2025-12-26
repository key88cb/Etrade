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
  startTime?: number;
  endTime?: number;
  taskId?: string | number;
}

interface PriceComparisonParams {
  startTime: number;
  endTime: number;
  taskId?: string | number;
}

export interface TaskListParams {
  page?: number;
  limit?: number;
}

export interface CancelTaskPayload {
  reason?: string;
}

export interface TemplatePayload {
  name: string;
  task_type: string;
  config: Record<string, unknown>;
}

export interface BatchPayload {
  name: string;
  description?: string;
  refreshed?: boolean;
}

export interface ReportPayload {
  batch_id: number;
  template_id?: number;
  format: string;
  file_path?: string;
}

export interface ExperimentPayload {
  batch_id: number;
  description?: string;
}

const api = {
  getOpportunities: (params?: OpportunitiesParams) =>
    instance.get('/opportunities', { params }),
  getPriceComparisonData: (params: PriceComparisonParams) =>
    instance.get('/price-comparison', { params }),
  getTasks: (params?: TaskListParams) => instance.get('/tasks', { params }),
  getTaskDetail: (taskId: string) => instance.get(`/tasks/${taskId}`),
  getTaskLogs: (taskId: string, params?: { limit?: number; offset?: number }) =>
    instance.get(`/tasks/${taskId}/logs`, { params }),
  cancelTask: (taskId: string, payload?: CancelTaskPayload) =>
    instance.post(`/tasks/${taskId}/cancel`, payload),
  getTemplates: () => instance.get('/templates'),
  createTemplate: (payload: TemplatePayload) => instance.post('/templates', payload),
  updateTemplate: (id: number, payload: TemplatePayload) =>
    instance.put(`/templates/${id}`, payload),
  deleteTemplate: (id: number) => instance.delete(`/templates/${id}`),
  runTemplate: (id: number, payload?: { task_id?: string; trigger?: string; overrides?: Record<string, unknown> }) =>
    instance.post(`/templates/${id}/run`, payload),
  getBatches: () => instance.get('/batches'),
  createBatch: (payload: BatchPayload) => instance.post('/batches', payload),
  updateBatch: (id: number, payload: BatchPayload) => instance.put(`/batches/${id}`, payload),
  getReports: (params?: { batch_id?: number }) => instance.get('/reports', { params }),
  createReport: (payload: ReportPayload) => instance.post('/reports', payload),
  
  // 🌟 新增：删除报告接口
  deleteReport: (id: number) => instance.delete(`/reports/${id}`),

  // Experiments
  getExperiments: (params?: { batch_id?: number }) => instance.get('/experiments', { params }),
  createExperiment: (payload: ExperimentPayload) => instance.post('/experiments', payload),
  getExperiment: (id: number) => instance.get(`/experiments/${id}`),
  getExperimentRuns: (id: number) => instance.get(`/experiments/${id}/runs`),
  runExperiment: (
    id: number,
    payload: { template_id: number; task_id?: string; trigger?: string; overrides?: Record<string, unknown> },
  ) => instance.post(`/experiments/${id}/runs`, payload),
};

export default api;
