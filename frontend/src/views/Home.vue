<template>
  <div class="home-container">
    <a-card class="welcome-card" :bordered="false">
      <div class="logo-section">
        <img src="/logo.png" alt="Etrade Logo" class="logo-image" />
        <h1 class="project-title">Etrade</h1>
        <p class="project-subtitle">发现 CEX 与 DEX 之间的历史套利机会</p>
      </div>

      <a-divider />

      <div class="description-section">
        <p>
          欢迎使用 Etrade ！本平台旨在通过分析历史交易数据，
          可视化展示中心化交易所 (Binance) 与去中心化交易所 (Uniswap V3)
          之间的价格差异，并识别潜在的非原子套利机会。
        </p>
        <p>
          请选择您感兴趣的功能模块：
        </p>
      </div>

      <div class="navigation-buttons">
        <a-button type="primary" size="large" @click="goToComparison" class="nav-button">
          <LineChartOutlined />
          价格可视化对比
        </a-button>
        <a-button type="primary" size="large" @click="goToOpportunities" class="nav-button" ghost>
           <DollarOutlined />
          套利机会列表
        </a-button>
        </div>
    </a-card>

    <footer class="home-footer">
      © {{ new Date().getFullYear() }} SRE2025FallGroup. All Rights Reserved.
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { LineChartOutlined, DollarOutlined } from '@ant-design/icons-vue';

const router = useRouter();

const goToComparison = () => {
  // 确保你的路由配置中 '/comparison' 指向 PriceComparisonView.vue
  router.push('/comparison'); 
};

const goToOpportunities = () => {
  // 确保你的路由配置中 '/opportunities' 指向 OpportunitiesView.vue
  router.push('/opportunities'); 
};
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f0f2f5 0%, #e6f7ff 100%); /* 淡雅渐变背景 */
  padding: 40px 20px;
  box-sizing: border-box;
}

.welcome-card {
  width: 100%;
  max-width: 800px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.logo-section {
  margin-bottom: 30px;
}

.logo-image {
  width: fit-content; /* 根据你的Logo调整大小 */
  height: fit-content;
  margin-bottom: 20px;
  animation: bounceIn 1s ease;
}

@keyframes bounceIn {
  0%, 20%, 40%, 60%, 80%, 100% {
    animation-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
  }
  0% { opacity: 0; transform: scale3d(.3, .3, .3); }
  20% { transform: scale3d(1.1, 1.1, 1.1); }
  40% { transform: scale3d(.9, .9, .9); }
  60% { opacity: 1; transform: scale3d(1.03, 1.03, 1.03); }
  80% { transform: scale3d(.97, .97, .97); }
  100% { opacity: 1; transform: scale3d(1, 1, 1); }
}

.project-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.project-subtitle {
  font-size: 16px;
  color: #666;
  margin-bottom: 30px;
}

.description-section p {
  font-size: 16px;
  color: #555;
  line-height: 1.8;
  margin-bottom: 20px;
}

.navigation-buttons {
  margin-top: 40px;
  display: flex;
  justify-content: center;
  gap: 20px; /* 按钮间距 */
}

.nav-button {
  min-width: 200px; /* 固定按钮宽度 */
  border-radius: 8px;
  transition: all 0.3s ease;
}

.nav-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
}

.home-footer {
  margin-top: 30px;
  font-size: 14px;
  color: #999;
}
</style>