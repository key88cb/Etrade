// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('../views/Home.vue')
    },
    {
      path: '/comparison',
      name: 'PriceComparison',
      component: () => import('../views/PriceComparisonView.vue')
    },
    {
      path: '/opportunities',
      name: 'Opportunities',
      component: () => import('../views/OpportunitiesView.vue')
    }
  ]
})

export default router
