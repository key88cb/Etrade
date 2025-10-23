import axios from 'axios';

// 本地开发可以选择 localhost:8888/api
// 如果需要局域网内访问，将 localhost 改为你的内网 ip 地址
export const backendURL = 'http://localhost:8888/api/v1';

// 创建axios实例
const instance = axios.create({
    baseURL: backendURL,
    timeout: 5000,
    headers: {
      'Content-Type': 'application/json'
    }
  });

// 响应拦截器处理错误
instance.interceptors.response.use(
    (response) => {
      return response;
    },
    (error) => {
      return Promise.reject(error.response?.data || '请求失败');
    }
  );

const api = {
  getOpportunities: () => {
    return instance.get('/opportunities');
  },
  /**
   * 获取用于价格对比图表的数据
   */
  getPriceComparisonData: () => {
    return instance.get('/price-comparison');
  }
}

export default api;