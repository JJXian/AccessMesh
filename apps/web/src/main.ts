import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './styles/main.css'

// 在根应用上统一注册状态管理、路由和 Element Plus 组件库。
createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
