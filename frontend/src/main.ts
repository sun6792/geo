import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'
import { setupStores, useAuthStore } from './store'

import './styles/reset.scss'
import './styles/common.scss'

const app = createApp(App)

app.use(ElementPlus, { locale: zhCn })
app.use(router)
setupStores(app)

app.mount('#app')

// On every page load, verify role from server (prevents stale localStorage bypass)
const authStore = useAuthStore()
authStore.initAuth()
