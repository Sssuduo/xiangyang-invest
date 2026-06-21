import api from './index'

// 导入字段配置
export function getImportFields() {
  return api.get('/admin/import/fields')
}

export function updateImportFields(data) {
  return api.put('/admin/import/fields', data)
}

// 下载导入模板（使用 fetch 支持 blob）
export async function downloadImportTemplate() {
  const resp = await fetch('/api/admin/import/template', { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '项目导入模板.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 导入预览（使用 fetch 支持 FormData）
export async function importPreviewApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await fetch('/api/admin/import/preview', {
    method: 'POST',
    credentials: 'same-origin',
    body: formData
  })
  const data = await resp.json()
  if (!resp.ok || data.code !== 0) {
    throw new Error(data.message || '预览失败')
  }
  return data
}

// 执行导入
export function importExecute(rows) {
  return api.post('/admin/import/execute', { rows })
}
