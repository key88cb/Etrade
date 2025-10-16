import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../views/Home.vue')
    },
    {
      path: '/echarts',
      component: () => import('../views/EchartsDemo.vue')
    }
  ]
})

export default router