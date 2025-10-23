// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home', // 给主页命名
      component: () => import('../views/Home.vue') // 新的Home页
    },
    {
      path: '/comparison', // 价格对比页的路径
      name: 'PriceComparison',
      component: () => import('../views/PriceComparisonView.vue')
    },
    {
      path: '/opportunities', // 套利机会页的路径
      name: 'Opportunities',
      component: () => import('../views/OpportunitiesView.vue') 
    }
  ]
})

export default router