import { ref, watch } from 'vue'

// Debug 状态存储在 localStorage 中，跨页面/刷新保持
const STORAGE_KEY = 'xiangyang_debug_mode'

const isDebugEnabled = ref(
  localStorage.getItem(STORAGE_KEY) === 'true'
)

// 监听变化自动持久化
watch(isDebugEnabled, (val) => {
  localStorage.setItem(STORAGE_KEY, val ? 'true' : 'false')
})

export function useDebug() {
  function enable() {
    isDebugEnabled.value = true
  }

  function disable() {
    isDebugEnabled.value = false
  }

  function toggle() {
    isDebugEnabled.value = !isDebugEnabled.value
  }

  /**
   * 格式化错误信息，debug 模式下返回完整堆栈
   */
  function formatError(err) {
    if (!isDebugEnabled.value) {
      return err.message || '操作失败'
    }

    // Debug 模式：返回完整错误信息
    const parts = []

    if (err.message) {
      parts.push(`[消息] ${err.message}`)
    }

    if (err.response?.data) {
      const respData = err.response.data
      if (respData.message) {
        parts.push(`[服务器消息] ${respData.message}`)
      }
      if (respData.traceback) {
        parts.push(`[服务器堆栈]\n${respData.traceback}`)
      }
      parts.push(`[HTTP状态] ${err.response.status} ${err.response.statusText}`)
      parts.push(`[请求URL] ${err.config?.method?.toUpperCase()} ${err.config?.url}`)
    }

    if (err.stack && isDebugEnabled.value) {
      parts.push(`[客户端堆栈]\n${err.stack}`)
    }

    // 如果没有任何信息，返回序列化的对象
    if (parts.length === 0) {
      try {
        parts.push(JSON.stringify(err, null, 2))
      } catch {
        parts.push(String(err))
      }
    }

    return parts.join('\n')
  }

  /**
   * 包装一个 API 调用，在 debug 模式下捕获并显示完整错误
   */
  async function debugWrap(fn, context = '') {
    try {
      return await fn()
    } catch (err) {
      const msg = formatError(err)
      const fullMsg = context ? `[${context}] ${msg}` : msg

      if (isDebugEnabled.value) {
        console.group('🐛 Debug Error')
        console.error(fullMsg)
        console.groupEnd()
      }

      throw new Error(fullMsg)
    }
  }

  return {
    isDebugEnabled,
    enable,
    disable,
    toggle,
    formatError,
    debugWrap
  }
}
