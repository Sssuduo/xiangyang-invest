import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'
import './assets/styles/main.css'
import './assets/styles/demand-button-fix.css'

// 诉求卡片编辑/删除按钮颜色（修复全局 --el-color-primary 被覆盖导致颜色过深）
// 动态注入样式（绕过 Vite 对 Vue 组件 CSS 的提取问题）
if (typeof document !== 'undefined' && !document.getElementById('demand-card-actions-style')) {
  const style = document.createElement('style')
  style.id = 'demand-card-actions-style'
  style.textContent = '.demand-card-actions .el-button.is-link{font-weight:500}.demand-card-actions .el-button--primary.is-link{color:#409eff}.demand-card-actions .el-button--danger.is-link{color:#f56c6c}.demand-card-actions .el-button.is-link .el-icon{color:inherit}'
  document.head.appendChild(style)
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
