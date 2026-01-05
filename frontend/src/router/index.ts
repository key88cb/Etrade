// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Welcome',
      component: () => import('../views/Welcome.vue'),
    },
    {
      path: '/app',
      component: () => import('../layouts/AppLayout.vue'),
      children: [
        { path: '', redirect: '/app/tasks' },
        {
          path: 'tasks',
          name: 'TaskCenter',
          meta: { title: '任务中心' },
          component: () => import('../views/TaskCenterView.vue'),
        },
        {
          path: 'batches',
          name: 'Batches',
          meta: { title: '批次管理' },
          component: () => import('../views/BatchesView.vue'),
        },
        {
          path: 'opportunities',
          name: 'Opportunities',
          meta: { title: '机会中心' },
          component: () => import('../views/OpportunitiesView.vue'),
        },
        {
          path: 'reports',
          name: 'Reports',
          meta: { title: '报告中心' },
          component: () => import('../views/ReportsView.vue'),
        },
        {
          path: 'comparison',
          name: 'PriceComparison',
          meta: { title: '价格对比' },
          component: () => import('../views/PriceComparisonView.vue'),
        },
        {
          path: 'templates',
          name: 'Templates',
          meta: { title: '模板管理' },
          component: () => import('../views/TemplatesView.vue'),
        },
        {
          path: 'history',
          name: 'History',
          meta: { title: '历史回放' },
          component: () => import('../views/HistoryView.vue'),
        },
        {
          path: 'overview',
          name: 'Overview',
          meta: { title: '运行任务' },
          component: () => import('../views/Home.vue'),
        },
      ],
    },

    // Legacy paths (redirects)
    { path: '/tasks', redirect: '/app/tasks' },
    { path: '/batches', redirect: '/app/batches' },
    { path: '/opportunities', redirect: '/app/opportunities' },
    { path: '/reports', redirect: '/app/reports' },
    { path: '/comparison', redirect: '/app/comparison' },
    { path: '/templates', redirect: '/app/templates' },
    { path: '/history', redirect: '/app/history' },
  ]
})

export default router
