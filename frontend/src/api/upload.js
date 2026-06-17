/**
 * 图片上传
 *
 * 优先走 Vite 代理，如果代理失败则直连后端（绕过 Vite 对 multipart 的潜在兼容问题）
 * 返回详细的错误信息，支持 debug 模式
 */

function isDebugEnabled() {
  return localStorage.getItem('xiangyang_debug_mode') === 'true'
}

async function doUpload(url, formData) {
  const response = await fetch(url, {
    method: 'POST',
    body: formData
    // 不设 Content-Type，浏览器自动生成含 boundary 的 multipart/form-data
  })

  const contentType = response.headers.get('content-type') || ''

  let data
  if (contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      const text = await response.text().catch(() => '')
      throw new Error(`服务器返回无法解析的内容 (HTTP ${response.status}): ${text.substring(0, 300)}`)
    }
  } else {
    const text = await response.text().catch(() => '')
    throw new Error(`服务器返回非 JSON (HTTP ${response.status}, ${contentType}): ${text.substring(0, 300)}`)
  }

  if (!response.ok || data.code !== 0) {
    const parts = [data.message || `请求失败 (HTTP ${response.status})`]
    if (isDebugEnabled() && data.traceback) {
      parts.push('\n【服务器堆栈】' + data.traceback)
    }
    throw new Error(parts.join('\n'))
  }

  return data
}

export async function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const urls = [
    'http://localhost:5000/api/upload',       // 优先：直连（大文件更可靠）
    '/api/upload'                             // 降级：Vite 代理
  ]

  const errors = []

  for (const url of urls) {
    try {
      if (isDebugEnabled()) {
        console.log(`[上传] 尝试: ${url}`)
      }
      const data = await doUpload(url, formData)
      if (isDebugEnabled()) {
        console.log(`[上传] 成功: ${url} -> ${data.data.url}`)
      }
      return data
    } catch (err) {
      const label = url === urls[0] ? '代理' : '直连'
      errors.push(`[${label}] ${err.message}`)
      if (isDebugEnabled()) {
        console.warn(`[上传] ${label} 失败:`, err)
      }
    }
  }

  // 所有 URL 都失败
  const parts = ['图片上传失败']
  parts.push(...errors)
  if (isDebugEnabled()) {
    parts.push(`\n【文件】${file.name} (${(file.size / 1024).toFixed(1)}KB)`)
  }

  throw new Error(parts.join('\n'))
}
