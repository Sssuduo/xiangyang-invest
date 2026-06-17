import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 从 localStorage 读取 debug 模式（与 utils/debug.js 共用 key）
function isDebugEnabled() {
  return localStorage.getItem('xiangyang_debug_mode') === 'true'
}

// 请求拦截器
api.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    // 提取尽量多的错误信息
    let message = '请求失败'
    const parts = []

    if (error.response?.data?.message) {
      parts.push(error.response.data.message)
    }
    if (error.response?.status) {
      parts.push(`[HTTP ${error.response.status}]`)
    }
    if (error.message && !error.response) {
      parts.push(error.message)
    }

    if (parts.length > 0) {
      message = parts.join(' ')
    }

    // Debug 模式：构建完整错误信息
    if (isDebugEnabled()) {
      const debugParts = [message]
      if (error.response?.data?.traceback) {
        debugParts.push('\n【服务器堆栈】')
        debugParts.push(error.response.data.traceback)
      }
      debugParts.push('\n【请求详情】')
      debugParts.push(`URL: ${error.config?.method?.toUpperCase() || '?'} ${error.config?.url || '?'}`)
      if (error.response?.status) {
        debugParts.push(`状态码: ${error.response.status}`)
      }
      if (error.config?.data) {
        debugParts.push(`请求体: ${error.config.data}`)
      }
      message = debugParts.join('\n')
    }

    return Promise.reject(new Error(message))
  }
)

export default api
