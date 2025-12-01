import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import { initTheme } from './utils/theme'

// 在应用启动前初始化主题
initTheme()

const app = createApp(App)
app.use(router)
app.use(Antd)
app.mount('#app')
