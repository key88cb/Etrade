<template>
  <a-config-provider :theme="antdTheme">
    <router-view></router-view>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { theme } from 'ant-design-vue'
import { isDarkMode } from './utils/theme'

const darkMode = ref(isDarkMode())

// 计算 Ant Design Vue 的主题配置
const antdTheme = computed(() => ({
  algorithm: darkMode.value ? theme.darkAlgorithm : theme.defaultAlgorithm,
}))

// 监听主题变化
const checkTheme = () => {
  darkMode.value = isDarkMode()
}

onMounted(() => {
  // 初始检查
  checkTheme()
  
  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const handleChange = () => {
    checkTheme()
  }
  
  mediaQuery.addEventListener('change', handleChange)
  
  // 监听 DOM 变化（当主题被手动切换时）
  const observer = new MutationObserver(() => {
    checkTheme()
  })
  
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })
})
</script>

<style>
</style>