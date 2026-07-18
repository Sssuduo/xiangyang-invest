// === 错误捕获:在页面顶部显示红色错误条(不遮画面) ===
// 关键:所有对 document.body 的操作都延后到 DOMContentLoaded 之后,
// 避免主脚本在 <head> 里同步执行时为 null 导致整个应用加载链崩溃。
(function() {
  const QUEUE = []   // body 还没准备好时暂存消息
  let box = null

  function ensureBox() {
    if (box) return true
    if (!document.body) return false
    box = document.createElement('div')
    box.id = '__global_err'
    box.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#fee;color:#c00;padding:8px 16px;z-index:99999;font-size:12px;max-height:30vh;overflow:auto;white-space:pre-wrap;border-bottom:2px solid #c00;font-family:monospace;'
    document.body.prepend(box)
    return true
  }

  function showErr(msg) {
    if (!ensureBox()) { QUEUE.push(msg); return }
    const div = document.createElement('div')
    div.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg
    box.appendChild(div)
  }

  function flushQueue() {
    if (!ensureBox()) return
    while (QUEUE.length) showErr(QUEUE.shift())
  }

  window.addEventListener('error', function(e) {
    showErr('JS_ERROR: ' + e.message + ' @ ' + (e.filename||'') + ':' + (e.lineno||''))
  })
  window.addEventListener('unhandledrejection', function(e) {
    showErr('PROMISE_REJECT: ' + (e.reason?.message || String(e.reason)))
  })
  const _consoleError = console.error
  console.error = function(...args) {
    showErr('CONSOLE_ERROR: ' + args.map(String).join(' '))
    _consoleError.apply(console, args)
  }

  window.addEventListener('DOMContentLoaded', function() {
    flushQueue()
    let tries = 0
    const hook = setInterval(function() {
      tries++
      const app = window.__APP__
      if (app && app.config && app.config.errorHandler !== vueHandler) {
        app.config.errorHandler = vueHandler
        clearInterval(hook)
      } else if (tries > 200) { clearInterval(hook) }
    }, 50)
  })

  function vueHandler(err, instance, info) {
    const where = instance && instance.$options && (instance.$options.name || instance.$options.__name)
    showErr('VUE_ERROR ' + (info || '') + (where ? ' @' + where : '') + ': ' + (err && err.message || err))
    if (err && err.console !== false) _consoleError('[VueError]', err)
  }
})()

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'
import './assets/styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

window.__APP__ = app

app.mount('#app')
